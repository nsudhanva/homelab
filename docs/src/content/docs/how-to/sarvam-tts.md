---
title: Speak Kannada with Sarvam TTS
description: Use the Sarvam text-to-speech integration in Home Assistant to play Kannada speech on the Google Home speaker.
keywords:
  - sarvam tts home assistant
  - kannada text to speech
  - bulbul v4 flash
  - google home kannada
sidebar:
  order: 8
---

# Speak Kannada with Sarvam TTS

Home Assistant uses the Sarvam AI text-to-speech API to make Kannada speech. The Cast integration plays the audio on the Google Home speaker `media_player.living_room_speaker`.

## Components

| Item | Value |
| --- | --- |
| Integration code | `apps/home-assistant/custom_components/sarvam_tts/` |
| Configuration | `sarvam.yaml` in `apps/home-assistant/configmap-packages.yaml` |
| API key | Vault `kv/sarvam` (`api_key`), synced by `apps/home-assistant/external-secret-sarvam.yaml` to the Secret `sarvam-api` |
| Model | `bulbul:v4-flash` |
| Language | `kn-IN` |
| Voice | `chaitra_kn_conversation` (female, conversation style) |
| Action | `tts.sarvam_tts_say` |
| Script | `script.say_kannada` |

Kustomize puts the integration files in the ConfigMap `home-assistant-sarvam-tts`. The ConfigMap name has a content hash, so a change to the code restarts Home Assistant. The Deployment reads the API key from the Secret into the environment variable `SARVAM_API_KEY`.

## Step 1: Store the API key

Store the Sarvam API key in Vault:

```bash
kubectl -n vault exec -it vault-0 -- vault kv put kv/sarvam api_key="REPLACE_ME"
```

External Secrets syncs the key into the `home-assistant` namespace. The refresh interval is one hour. Home Assistant reads the key when it starts.

## Step 2: Play Kannada speech

Write the text in Kannada script. The model reads transliterated text with lower quality.

In Home Assistant, open **Settings > Automations & scenes > Scripts**, select **Say in Kannada**, and enter the message. The script plays the message on `media_player.living_room_speaker` by default.

To use the action in an automation, call `tts.sarvam_tts_say`:

```yaml
action: tts.sarvam_tts_say
data:
  entity_id: media_player.living_room_speaker
  message: ನಮಸ್ಕಾರ, ಮನೆಯ ಸಹಾಯಕ ಸಿದ್ಧವಾಗಿದೆ.
```

## Step 3: Change the voice

Set the voice for one call with `options`:

```yaml
action: tts.sarvam_tts_say
data:
  entity_id: media_player.living_room_speaker
  message: ನಮಸ್ಕಾರ
  options:
    speaker: suchitra_kn_narration
    pace: 1.1
```

To change the default voice, edit `speaker` in `sarvam.yaml` and push the change. The Kannada voices for `bulbul:v4-flash` are `chaitra_kn_conversation`, `chaitra_kn_narration`, `chetan_kn_conversation`, and `suchitra_kn_narration`.

## Limits

- The API accepts 2,500 characters in one request. The integration splits longer text at the end of a sentence and joins the audio.
- `pace` accepts values from 0.5 to 2.0.
- The integration requests MP3 audio at 24,000 Hz.
- If the API returns an error, Home Assistant logs the error from `custom_components.sarvam_tts.tts` and plays no audio.

For the API reference, refer to the [Sarvam text-to-speech documentation](https://docs.sarvam.ai/api-reference-docs/text-to-speech/convert).
