# Drive Organizer

A Google Drive organizer that runs as a daily CronJob per Google account on bare-metal K3s. It uses the shared `homelab-ai` model chain (Claude Haiku 5.5 first) to classify documents from their extracted text and file them into the same folder structure for each person. Joint documents get a full copy in the spouse folder.
