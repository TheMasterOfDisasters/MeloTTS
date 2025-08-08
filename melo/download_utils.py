
import torch
import os
from . import utils
from cached_path import cached_path
from huggingface_hub import hf_hub_download

DOWNLOAD_CKPT_URLS = {
    'EN': 'https://myshell-public-repo-host.s3.amazonaws.com/openvoice/basespeakers/EN/checkpoint.pth',
    'EN_V2': 'https://myshell-public-repo-host.s3.amazonaws.com/openvoice/basespeakers/EN_V2/checkpoint.pth',
    'FR': 'https://myshell-public-repo-host.s3.amazonaws.com/openvoice/basespeakers/FR/checkpoint.pth',
    'JP': 'https://myshell-public-repo-host.s3.amazonaws.com/openvoice/basespeakers/JP/checkpoint.pth',
    'ES': 'https://myshell-public-repo-host.s3.amazonaws.com/openvoice/basespeakers/ES/checkpoint.pth',
    'ZH': 'https://myshell-public-repo-host.s3.amazonaws.com/openvoice/basespeakers/ZH/checkpoint.pth',
    'KR': 'https://myshell-public-repo-host.s3.amazonaws.com/openvoice/basespeakers/KR/checkpoint.pth',
}

DOWNLOAD_CONFIG_URLS = {
    'EN': 'https://myshell-public-repo-host.s3.amazonaws.com/openvoice/basespeakers/EN/config.json',
    'EN_V2': 'https://myshell-public-repo-host.s3.amazonaws.com/openvoice/basespeakers/EN_V2/config.json',
    'FR': 'https://myshell-public-repo-host.s3.amazonaws.com/openvoice/basespeakers/FR/config.json',
    'JP': 'https://myshell-public-repo-host.s3.amazonaws.com/openvoice/basespeakers/JP/config.json',
    'ES': 'https://myshell-public-repo-host.s3.amazonaws.com/openvoice/basespeakers/ES/config.json',
    'ZH': 'https://myshell-public-repo-host.s3.amazonaws.com/openvoice/basespeakers/ZH/config.json',
    'KR': 'https://myshell-public-repo-host.s3.amazonaws.com/openvoice/basespeakers/KR/config.json',
}

PRETRAINED_MODELS = {
    'G.pth': 'https://myshell-public-repo-host.s3.amazonaws.com/openvoice/basespeakers/pretrained/G.pth',
    'D.pth': 'https://myshell-public-repo-host.s3.amazonaws.com/openvoice/basespeakers/pretrained/D.pth',
    'DUR.pth': 'https://myshell-public-repo-host.s3.amazonaws.com/openvoice/basespeakers/pretrained/DUR.pth',
}

LANG_TO_HF_REPO_ID = {
    'EN': 'myshell-ai/MeloTTS-English',
    'EN_V2': 'myshell-ai/MeloTTS-English-v2',
    'EN_NEWEST': 'myshell-ai/MeloTTS-English-v3',
    'FR': 'myshell-ai/MeloTTS-French',
    'JP': 'myshell-ai/MeloTTS-Japanese',
    'ES': 'myshell-ai/MeloTTS-Spanish',
    'ZH': 'myshell-ai/MeloTTS-Chinese',
    'KR': 'myshell-ai/MeloTTS-Korean',
}

def _check_offline_path(language, filename):
    root_dir = os.getenv("MELOTTTS_MODELS")
    if not root_dir:
        return None
    # Expected structure: <root>/models/<LANG>/<type>/<file>
    if filename == "checkpoint.pth":
        candidate = os.path.join(root_dir, "models", language, "model", filename)
    elif filename == "config.json":
        candidate = os.path.join(root_dir, "models", language, "config", filename)
    else:
        return None

    if os.path.exists(candidate):
        print(f"[INFO] Using local {filename} from {candidate}")
        return candidate
    else:
        raise FileNotFoundError(
            f"[ERROR] Expected {filename} for language {language} at {candidate}, "
            "but file was not found. Please ensure the offline model structure is correct."
        )

def load_or_download_config(locale, use_hf=True, config_path=None):
    language = locale.split('-')[0].upper()

    if config_path is None:
        # First try offline mode
        offline_config = _check_offline_path(language, "config.json")
        if offline_config:
            config_path = offline_config
        else:
            # Online fallback
            if use_hf:
                assert language in LANG_TO_HF_REPO_ID
                config_path = hf_hub_download(repo_id=LANG_TO_HF_REPO_ID[language], filename="config.json")
            else:
                assert language in DOWNLOAD_CONFIG_URLS
                config_path = cached_path(DOWNLOAD_CONFIG_URLS[language])

    return utils.get_hparams_from_file(config_path)

def load_or_download_model(locale, device, use_hf=True, ckpt_path=None):
    language = locale.split('-')[0].upper()

    if ckpt_path is None:
        # First try offline mode
        offline_ckpt = _check_offline_path(language, "checkpoint.pth")
        if offline_ckpt:
            ckpt_path = offline_ckpt
        else:
            # Online fallback
            if use_hf:
                assert language in LANG_TO_HF_REPO_ID
                ckpt_path = hf_hub_download(repo_id=LANG_TO_HF_REPO_ID[language], filename="checkpoint.pth")
            else:
                assert language in DOWNLOAD_CKPT_URLS
                ckpt_path = cached_path(DOWNLOAD_CKPT_URLS[language])

    return torch.load(ckpt_path, map_location=device)

def load_pretrain_model():
    return [cached_path(url) for url in PRETRAINED_MODELS.values()]
