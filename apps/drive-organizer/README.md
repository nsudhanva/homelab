# Drive Organizer

A Google Drive organizer that runs as a daily CronJob for each Google account on the bare-metal K3s cluster. It uses the shared `homelab-ai` model chain (Claude Haiku 5.5 first) to classify documents from their extracted text. It files each document into the same folder structure for each person. A joint document gets a full copy in the folder of the spouse.
