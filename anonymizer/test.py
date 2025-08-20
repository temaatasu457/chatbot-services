import time
from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

text = "АО  «РАЙФФАЙЗЕНБАНК», БИК 044525700, К/с 30101810200000000700 г.Москва, ИНН 7744000302 RZBMRUMM RUB 30111810600000000013 Российский рубль"

# Configuratio
configuration = {"nlp_engine_name" : "spacy", "models" : [{"lang_code" : "ru", "model_name" : "ru_core_news_md"},
                                                          {"lang_code" : "en", "model_name" : "en_core_web_md"}]}

card_pattern = Pattern(name="card_pattern", regex="\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{1,4}", score=0.5)

iban_pattern = Pattern(name="iban_pattern", regex="KZ[0-9]{2}[0-9A-Z]{16}", score=0.5)

kz_phone_pattern = Pattern(name="kz_phone_pattern", regex="(?:\+7|7|8)(?:7[0-7]|6[0-9])\d{8}", score=0.5)

iin_bin_pattern = Pattern(name="iin_bin_pattern", regex="\d{12}", score=0.5)

account_pattern = Pattern(name="account_pattern", regex="\d{20}", score=0.5)

card_recognizer = PatternRecognizer(supported_entity="CARD",
                                    patterns=[card_pattern],
                                    supported_language="ru",
                                    context=["карта", "номер карты"])

iban_recognizer = PatternRecognizer(supported_entity="IBAN",
                                        patterns=[iban_pattern],
                                        supported_language="ru",
                                        context=["iban"])

kz_phone_recognizer = PatternRecognizer(supported_entity="KZ_PHONE_NUMBER",
                                        patterns=[kz_phone_pattern],
                                        supported_language="ru",
                                        context=["номер", "телефон", "номер телефона"])

iin_bin_recognizer = PatternRecognizer(supported_entity="IIN_BIN_NUMBER",
                                        patterns=[iin_bin_pattern],
                                        supported_language="ru",
                                        context=["иин"])

account_recognizer = PatternRecognizer(supported_entity="ACCOUNT_NUMBER",
                                        patterns=[account_pattern],
                                        supported_language="ru",
                                        context=["счет", "счёт", "к/c"])

provider = NlpEngineProvider(nlp_configuration=configuration)
nlp_engine = provider.create_engine()
analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["ru", "en"])
analyzer.registry.recognizers.extend([card_recognizer, iban_recognizer, kz_phone_recognizer, iin_bin_recognizer, account_recognizer])
engine = AnonymizerEngine()

start = time.time()
analyzer_results = analyzer.analyze(text=text, language="ru")
anonymizer_results = engine.anonymize(text=text,
                                      analyzer_results=analyzer_results,
                                      operators={"PERSON": OperatorConfig("replace", {"new_value": "<ИМЯ КЛИЕНТА>"}),
                                                 "LOCATION": OperatorConfig("replace", {"new_value": "<АДРЕС>"}),
                                                 "CREDIT_CARD": OperatorConfig("replace", {"new_value": "<НОМЕР КАРТЫ>"}),
                                                 "CARD": OperatorConfig("replace", {"new_value": "<НОМЕР КАРТЫ>"}),
                                                 "IBAN_CODE": OperatorConfig("replace", {"new_value": "<IBAN>"}),
                                                 "IBAN": OperatorConfig("replace", {"new_value": "<IBAN>"}),
                                                 "PHONE_NUMBER": OperatorConfig("replace", {"new_value": "<НОМЕР ТЕЛЕФОНА>"}),
                                                 "KZ_PHONE_NUMBER": OperatorConfig("replace", {"new_value": "<НОМЕР ТЕЛЕФОНА>"}),
                                                 "IIN_BIN_NUMBER": OperatorConfig("replace", {"new_value": "<ИИН/БИН>"}),
                                                 "ACCOUNT_NUMBER": OperatorConfig("replace", {"new_value": "<СЧЕТ>"})})
end = time.time()

# print(f'{analyzer_results}\n\n{anonymizer_results}')
print(f'{anonymizer_results.text}\n\nExecution time: {round(end-start, 4)}')