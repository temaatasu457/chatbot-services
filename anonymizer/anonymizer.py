import time
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig
from recognizer import card_recognizer, iban_recognizer, kz_phone_recognizer, iin_bin_recognizer, account_recognizer

OPERATORS = {
    "PERSON": OperatorConfig("replace", {"new_value": "<ИМЯ КЛИЕНТА>"}),
    "LOCATION": OperatorConfig("replace", {"new_value": "<АДРЕС>"}),
    "DATE_TIME": OperatorConfig("replace", {"new_value": "<ДАТА>"}),
    "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": "<ПОЧТА>"}),
    "CREDIT_CARD": OperatorConfig("replace", {"new_value": "<НОМЕР КАРТЫ>"}),
    "CARD": OperatorConfig("replace", {"new_value": "<НОМЕР КАРТЫ>"}),
    "IBAN_CODE": OperatorConfig("replace", {"new_value": "<IBAN>"}),
    "IBAN": OperatorConfig("replace", {"new_value": "<IBAN>"}),
    "PHONE_NUMBER": OperatorConfig("replace", {"new_value": "<НОМЕР ТЕЛЕФОНА>"}),
    "KZ_PHONE_NUMBER": OperatorConfig("replace", {"new_value": "<НОМЕР ТЕЛЕФОНА>"}),
    "IIN_BIN_NUMBER": OperatorConfig("replace", {"new_value": "<ИИН/БИН>"}),
    "ACCOUNT_NUMBER": OperatorConfig("replace", {"new_value": "<СЧЕТ>"}),
    "URL": OperatorConfig("replace", {"new_value": "<ССЫЛКА>"})
}

configuration = {"nlp_engine_name" : "spacy", "models" : [{"lang_code" : "ru", "model_name" : "ru_core_news_md"},
                                                          {"lang_code" : "en", "model_name" : "en_core_web_md"}]}
nlp_engine = NlpEngineProvider(nlp_configuration=configuration).create_engine()
analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["ru", "en"])
analyzer.registry.recognizers.extend([card_recognizer, iban_recognizer, kz_phone_recognizer, iin_bin_recognizer, account_recognizer])
engine = AnonymizerEngine()
    
def anonymize_text(self, language: str, text: str) -> str:
    analyzer_results = self.analyzer.analyze(text=text, language=language)
    print(f"Analyzer results: {analyzer_results}")
    anonymizer_results = self.engine.anonymize(text=text, analyzer_results=analyzer_results, operators=OPERATORS)
    return anonymizer_results.text

def main():
    language = "en"
    input_text = 'Не могу перевести деньги между своими счетами visa 4400 4302 1234 5059'
    start = time.time()
    anonymized_text = anonymize_text(language, input_text)
    end = time.time()
    print(f"Original text: {input_text}\nAnonymized text: {anonymized_text}\nExecution time: {round(end-start, 4)} sec")
    
if __name__=="__main__":
    main()