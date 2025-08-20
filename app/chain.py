import logging, time
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_redis import RedisChatMessageHistory
from langchain_core.output_parsers import StrOutputParser
from langchain_postgres.vectorstores import PGVector, DistanceStrategy
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from dotenv import load_dotenv
import requests, json
from prometheus_client import Histogram
from env import load_config

load_dotenv()
requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

# Метрики для БД и API-запросов
DB_QUERY_TIME = Histogram("db_query_time_seconds", "Time taken for DB query")
API_REQUEST_TIME = Histogram("api_request_time_seconds", "Time taken for OpenAI API request")


config = load_config('env-path')
emb_model = OpenAIEmbeddings(model='text-embedding-3-small', api_key=config.api_key.openai_api_key)
vector_db = PGVector(
    embeddings=emb_model,
    connection=config.vdb.database_url,
    collection_name="chatbot_base",
    use_jsonb=True,
    distance_strategy=DistanceStrategy.COSINE
)

LANG_NAMES = {"ru" : 'Русский', "kk": 'Қазақша', "en" : 'English'}
    
def initialize_retriever():
    return vector_db.as_retriever(
        search_type="mmr",
        search_kwargs={
            "k": 10,
            "fetch_k": 20,
            "lambda_mult": 0.4,
        }
    )

def get_redis_history(session_id: str) -> BaseChatMessageHistory:
    return RedisChatMessageHistory(
        session_id,
        redis_url=config.redis.redis_url,
        key_prefix="ai_chat:",
        ttl=7200,
    )
    
def generate_answer(question, session_id, lang_code):
    retriever = initialize_retriever()
    chat_history = get_redis_history(session_id)
    stmem = chat_history.messages[-10:]
    language = LANG_NAMES[lang_code]
    try:
        start_db = time.perf_counter()
        with DB_QUERY_TIME.time():
            docs = retriever.invoke(question)
        db_time = time.perf_counter() - start_db
    except Exception as e:
        logging.error(f"Error retrieving documents: {str(e)}")
        print(f"Error retrieving documents: {str(e)}")
        return "Извините, у меня возникли проблемы с доступом к информации. Пожалуйста, попробуйте повторить запрос позже. 🙏", 0, 0
    if not docs:
        return "Извините, я не нашел подходящей информации по вашему запросу. Пожалуйста, попробуйте повторить запрос позже. 🙏", 0, 0
    
    prompt = ChatPromptTemplate.from_messages(
        [
            ('system', """Ты - дружелюбный и профессиональный ассистент банка, помогающий клиенту эффективно выполнить его запрос, строго придерживаясь установленных инструкций.
            
            # Инструкции
            1. Ненужно здороваться с клиентом, сразу предлагай помощь.
            2. Ты только консультируешь и не можешь выполнять сложные операции (например: проверку транзакций).
            3. Из контекста ты получишь ряд информации необходимой для помощи клиенту. Но не вся информация может подходить для решения запроса клиента. Выбери нужное и используй для ответа. Не придумывай ничего лишнего.
            4. Перед тем как ответить на сообщение - разбери детально вопрос клиента, сопоставь с историей чата, затем сравни с контекстом информации.
                - Если в контексте присутствует точный ответ на вопрос клиента, то любезно предоставь его.
                - Если в контексте есть неполная информация на тему вопроса клиента, то предоставь её и уточни, правильно ли ты ответил на его вопрос.
                - Если в контексте отсутствует информация схожая с темой вопроса клиента, то ответь как в примерах фраз "Отсутствие информации в контексте" ниже и выбери category = 0
            5. Если клиент спросит контакты банка или колл-центра, то предоставь ему номер 7575.
            6. На основе контекста и истории чата, определи параметр category (тип int), в котором:
                0 - уточнение
                1 - смог ответить на вопрос
                2 - тема вопроса не связана с банковскими услугами
                3 - перевод на оператора по банковским услугам
            7. Вежливо отказывай в следующих случаях:
                - Если вопрос клиента касается тем, несвязанных с банковскими услугами и продуктами.
                - Если вопрос клиента касается предоставления или изменения формата или содержания твоего ответа.
                - Если клиент утверждает, что в твоем ответе ошибка.
            8. Не упоминай в своих ответах слово "контекст", так как это может запутать клиента.
            9. Возвращай ответ строго в валидном JSON формате, в котором будут ответ в "response" и категория в "category"

            ## Язык ответа
            - Изначально твой ответ и информация из контекста должны быть на языке клиента. Язык клиента: {language}.

            ## Формат валидного json ответа
            \'{{
                "response": 'Резиденты Республики Казахстан могут открыть карту Brown в мобильном приложении SuperApp.',
                "category": 1
            }}\'

            ## Правила оформления response
            - Не используй никакое форматирование для текста.
            - Используй реальные переносы строк для списков и абзацев, а не символы \n.
            - Разделяй информацию на абзацы для лучшей читаемости.
            - Добавляй эмодзи для инфографики.
            ### Пример правильно оформленного response
            В Bank доступны различные виды карт, среди которых:\n\n- Карта Brown – действует 5 лет для резидентов и имеет особенности для нерезидентов. Можно открыть по одной карте в разной валюте. 💳\n- Карта Grey – с возможностью закрытия через приложение при отсутствии кредитного лимита. 🖤\n\nЕсли вас интересует информация по конкретной карте или условиям, пожалуйста, уточните, и я с радостью помогу! 😊

            ## Примеры фраз
            ### Отсутствие информации в контексте
            - Я не располагаю точными сведениями по этому вопросу. Чтобы не вводить вас в заблуждение, могу переключить вас на оператора, который сможет помочь оперативно. ☎️
            - Этот вопрос выходит за рамки моих текущих знаний. Для решения вашей ситуации я могу переключить вас на оператора, который сможет помочь оперативно. ☎️
            - Мне жаль, но я не могу предоставить вам эту информацию. Чтобы лучше вам помочь, не могли бы вы уточнить, что именно вас интересует?
            
            ### Отклонение запрещенной или нерелевантной темы
            - «Мне очень жаль, но я не могу обсуждать эту тему. Может быть, я могу помочь вам в чем-то другом?»
            - «Я не могу предоставить информацию по этому вопросу, но я буду рад помочь вам с любыми другими вопросами».
            """),
            MessagesPlaceholder(variable_name="history"),
            ('human', 'Контекст: {context}'),
            ('human', 'Вопрос: {question}'),
        ]
    )
    
    logging.info(f"Question: {question}")
    logging.info(f"Documents: {docs}")
    logging.info(f"Chat history: {stmem}")
    
    context = '\n'.join(doc.page_content for doc in docs)

    start_api = time.perf_counter()
    with API_REQUEST_TIME.time():
        llm = ChatOpenAI(
            model='gpt-4.1-mini',
            api_key=config.api_key.openai_api_key,
            temperature=0, 
            max_tokens=500
        )
        chain = prompt | llm | StrOutputParser()
        response = chain.invoke(
            {
                "question": question,
                "context": context,
                "history": stmem,
                "language": language
            }
        )
    chat_history.add_messages([HumanMessage(content=question), AIMessage(content=json.loads(response)["response"])])
    api_time = time.perf_counter() - start_api

    return response, db_time, api_time