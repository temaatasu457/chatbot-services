import logging
from fasttext.FastText import _FastText

model = _FastText(model_path="../models/fasttext-language-identification.bin")
    
def identify_language(raw_text):
    try:
        text = raw_text.replace('\n', ' ')
        kz_group = {"kk", "ky", "tt", "mn", "az"}
        language_predictions = model.predict(text, k=5, threshold=0.01)
        languages = {lang[9:12]: score for lang, score in zip(language_predictions[0], language_predictions[1])}
        if "ru" in languages and languages["ru"] > 0.6:
            return "ru"
        elif kz_group.intersection(languages):
            return "kk"
        elif "en" in languages:
            return "en"
        else:
            return "ru"
    except Exception as e:
        logging.info(f"Couldn't identify language. Error: {e}")
        return "ru"