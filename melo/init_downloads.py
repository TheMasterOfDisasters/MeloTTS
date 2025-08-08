if __name__ == '__main__':
    from melo.api import TTS
    from transformers import AutoTokenizer, AutoModelForMaskedLM

    device = 'auto'

    # Step 1: Preload all TTS voice models
    languages = ['EN', 'ES', 'FR', 'ZH', 'JP', 'KR']
    models = {lang: TTS(language=lang, device=device) for lang in languages}

    # Step 2: Preload all BERT models used for text encoding
    bert_models = [
        "bert-base-uncased",                    # English
        "bert-base-multilingual-uncased",       # Chinese + misc.
        "dbmdz/bert-base-french-europeana-cased",# French
        "dccuchile/bert-base-spanish-wwm-uncased",# Spanish
        "kykim/bert-kor-base",                   # Korean
        "tohoku-nlp/bert-base-japanese-v3",     # Japanese
    ]

    def preload_bert(model_id):
        print(f"[INFO] Preloading BERT model: {model_id}")
        AutoTokenizer.from_pretrained(model_id)
        AutoModelForMaskedLM.from_pretrained(model_id, from_tf=False)  # PyTorch weights

    for mid in bert_models:
        preload_bert(mid)