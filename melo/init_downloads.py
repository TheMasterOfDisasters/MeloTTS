import os
import time


MAX_RETRIES = int(os.getenv("INIT_DOWNLOADS_MAX_RETRIES", "5"))
RETRY_SLEEP_SECONDS = int(os.getenv("INIT_DOWNLOADS_RETRY_SLEEP", "5"))
STRICT_MODE = os.getenv("INIT_DOWNLOADS_STRICT", "0") == "1"
DOWNLOAD_PROFILE = os.getenv("INIT_DOWNLOADS_PROFILE", "FULL").strip().upper()

FULL_LANGUAGES = ["EN", "EN_V2", "EN_NEWEST", "ES", "FR", "ZH", "JP", "KR"]
EN_ONLY_LANGUAGES = ["EN", "EN_V2", "EN_NEWEST"]

FULL_BERT_MODELS = [
    "bert-base-uncased",  # English
    "bert-base-multilingual-uncased",  # Chinese + misc.
    "dbmdz/bert-base-french-europeana-cased",  # French
    "dccuchile/bert-base-spanish-wwm-uncased",  # Spanish
    "kykim/bert-kor-base",  # Korean
    "tohoku-nlp/bert-base-japanese-v3",  # Japanese
]
EN_ONLY_BERT_MODELS = ["bert-base-uncased"]


def parse_csv_env(var_name):
    raw = os.getenv(var_name, "").strip()
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def resolve_preload_targets():
    explicit_languages = parse_csv_env("INIT_DOWNLOADS_LANGUAGES")
    explicit_bert_models = parse_csv_env("INIT_DOWNLOADS_BERT_MODELS")

    if explicit_languages:
        languages = explicit_languages
    elif DOWNLOAD_PROFILE == "EN_ONLY":
        languages = EN_ONLY_LANGUAGES
    else:
        languages = FULL_LANGUAGES

    if explicit_bert_models:
        bert_models = explicit_bert_models
    elif DOWNLOAD_PROFILE == "EN_ONLY":
        bert_models = EN_ONLY_BERT_MODELS
    else:
        bert_models = FULL_BERT_MODELS

    return languages, bert_models


def run_with_retries(name, fn):
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            fn()
            print(f"[INFO] Completed: {name}")
            return True
        except Exception as error:
            last_error = error
            print(f"[WARN] {name} failed on attempt {attempt}/{MAX_RETRIES}: {error}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_SLEEP_SECONDS * attempt)
    print(f"[ERROR] {name} failed after {MAX_RETRIES} attempts: {last_error}")
    return False


def preload_tts_language(language, device):
    def _load():
        from melo.api import TTS

        TTS(language=language, device=device)

    return run_with_retries(f"TTS model {language}", _load)


def preload_bert_model(model_id):
    def _load():
        from transformers import AutoTokenizer, AutoModelForMaskedLM

        AutoTokenizer.from_pretrained(model_id)
        AutoModelForMaskedLM.from_pretrained(model_id, from_tf=False)

    return run_with_retries(f"BERT model {model_id}", _load)


if __name__ == '__main__':
    device = 'auto'
    languages, bert_models = resolve_preload_targets()

    print(f"[INFO] INIT_DOWNLOADS_PROFILE={DOWNLOAD_PROFILE}")
    print(f"[INFO] Preloading TTS languages: {languages}")
    print(f"[INFO] Preloading BERT models: {bert_models}")

    # Step 1: Preload selected TTS voice models
    failed_items = []
    for lang in languages:
        if not preload_tts_language(lang, device=device):
            failed_items.append(f"TTS:{lang}")

    # Step 2: Preload selected BERT models used for text encoding
    for model_id in bert_models:
        if not preload_bert_model(model_id):
            failed_items.append(f"BERT:{model_id}")

    if failed_items:
        print(f"[WARN] Preload finished with failures: {failed_items}")
        if STRICT_MODE:
            raise RuntimeError("init_downloads failed in strict mode")
