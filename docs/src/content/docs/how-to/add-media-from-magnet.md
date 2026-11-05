---
title: Add a Movie or Show from a Magnet Link
description: Download a movie or a TV show from a magnet link, import it with Radarr or Sonarr, and watch it in Jellyfin with full metadata.
keywords:
  - magnet link jellyfin metadata
  - qbittorrent radarr manual import
  - jellyfin wrong movie title
  - radarr category movies
  - sonarr category tv
sidebar:
  order: 4
---

This guide starts with a magnet link and ends with the title in Jellyfin with its poster, plot, and cast.

Jellyfin gets metadata from the folder name and the file name. It needs the format `Title (Year)/Title (Year).ext`. Radarr and Sonarr rename the download to this format when they import it. A download that is not imported keeps its torrent name, and Jellyfin can show the wrong title or no metadata.

| Item | Movie | TV show |
| --- | --- | --- |
| Import app | Radarr, `https://radarr.sudhanva.me` | Sonarr, `https://sonarr.sudhanva.me` |
| qBittorrent category | `movies` | `tv` |
| Download folder | `/media/torrents/movies` | `/media/torrents/tv` |
| Library folder | `/media/movies` | `/media/tv` |

The steps use a movie. For a TV show, use Sonarr and the category `tv`.

## Step 1: Add the movie to Radarr

Radarr imports a file only for a movie that is in its library.

- In Radarr, open **Movies -> Add New**.
- Search for the movie title.
- Select the correct movie and its year.
- Clear **Start search for missing movie**.
- Select **Add Movie**.

## Step 2: Add the magnet link to qBittorrent

- Open `https://qbittorrent.sudhanva.me`.
- Select **Add Torrent Link** in the toolbar.
- Paste the magnet link, and select **Continue**.
- Set **Torrent Management Mode** to **Automatic**.
- Set **Category** to `movies`.
- Select **Download**.

The category tells Radarr that the download belongs to it. qBittorrent saves a download in the `movies` category to `/media/torrents/movies`.

## Step 3: Let Radarr import the download

When the download is complete, open **Activity -> Queue** in Radarr. If Radarr identifies the movie from the torrent name, it imports the file automatically. The import creates a hardlink in `/media/movies`, so the file uses no additional disk space.

If the queue shows a warning, or the torrent name does not contain the movie title, import the file manually:

- In Radarr, open **Wanted -> Missing**.
- Select **Manual Import** in the toolbar.
- Enter `/media/torrents/movies`, and select **Interactive Import**.
- Select the video file. If the **Movie** column is empty, select the movie from Step 1.
- Select **Import**.

## Step 4: Watch the movie in Jellyfin

Radarr tells Jellyfin to refresh the library after the import. Jellyfin also monitors `/media/movies` for new files. Open `https://jellyfin.sudhanva.me` and search for the title.

If Jellyfin shows the wrong movie, open the movie, select the **More** menu, and select **Identify**. Search for the title and the year, and select the correct result.

## Troubleshooting

| Problem | Cause | Action |
| --- | --- | --- |
| Jellyfin shows the file name, or a wrong title | The file is in the library folder with its torrent name | Import the file with Radarr (Step 3), or use **Identify** (Step 4) |
| Radarr does not show the download in the queue | The torrent has no category, or a category that is not `movies` | In qBittorrent, right-click the torrent, select **Category**, and select `movies` |
| Manual Import shows no movie for the file | The movie is not in the Radarr library | Do Step 1, then do the manual import again |
| qBittorrent shows the torrent as missing files | The files moved out of `/media/torrents` | Remove the torrent in qBittorrent and keep the files |

For the media stack configuration, refer to [Media Automation and WireGuard VPN Stack](/how-to/media-automation/).
