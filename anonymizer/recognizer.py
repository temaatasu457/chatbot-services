from presidio_analyzer import Pattern, PatternRecognizer

# Card recognizer
card_pattern = Pattern(name="card_pattern", regex="\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{1,4}", score=0.5)
card_recognizer = PatternRecognizer(supported_entity="CARD",
                                    patterns=[card_pattern],
                                    supported_language="ru",
                                    context=["карта", "номер карты"])

# IBAN recognizer
iban_pattern = Pattern(name="iban_pattern", regex="KZ[0-9]{2}[0-9A-Z]{16}", score=0.5)
iban_recognizer = PatternRecognizer(supported_entity="IBAN",
                                        patterns=[iban_pattern],
                                        supported_language="ru",
                                        context=["iban"])

# Phone recognizer
kz_phone_pattern = Pattern(name="kz_phone_pattern", regex="(?:\+\s?7|7|8)[\s-]?(?:7[0-7]|6[0-9])[\s-]?(?:\d[\s-]?){7}\d", score=0.5)
kz_phone_recognizer = PatternRecognizer(supported_entity="KZ_PHONE_NUMBER",
                                        patterns=[kz_phone_pattern],
                                        supported_language="ru",
                                        context=["номер", "телефон", "номер телефона"])

# IIN/BIN recognizer
iin_bin_pattern = Pattern(name="iin_bin_pattern", regex="\d{12}", score=0.5)
iin_bin_recognizer = PatternRecognizer(supported_entity="IIN_BIN_NUMBER",
                                        patterns=[iin_bin_pattern],
                                        supported_language="ru",
                                        context=["иин"])

# Account recognizer
account_pattern = Pattern(name="account_pattern", regex="\d{20}", score=0.5)
account_recognizer = PatternRecognizer(supported_entity="ACCOUNT_NUMBER",
                                        patterns=[account_pattern],
                                        supported_language="ru",
                                        context=["счет", "счёт", "к/c"])