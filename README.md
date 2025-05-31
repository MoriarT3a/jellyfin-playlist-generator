# Jellyfin Playlist Generator

A powerful tool to convert music playlists from various formats into Jellyfin-native XML playlists with intelligent track matching.

## 🎯 Why This Tool?

I was frustrated with the limitations of existing playlist conversion tools like Soundiiz when importing playlists to Jellyfin. Many tools either:
- Don't support Jellyfin's native format
- Have poor track matching accuracy  
- Don't handle edge cases well
- Require manual intervention for every mismatch

This tool was born out of that frustration, providing a robust solution with:
- **Multi-stage fuzzy matching** (99%+ success rate)
- **Intelligent fallback strategies**
- **Interactive selection** for edge cases
- **FLAC preference** for audiophiles
- **Live version filtering**
- **Native Jellyfin XML format**

## ✨ Features

- 🎵 **Multi-format support**: CSV, TXT playlist formats
- 🎯 **3-stage matching**: Strict → Medium → Loose automatic matching
- 🤝 **Interactive mode**: Manual selection for difficult matches
- 🎼 **Audio format preference**: Prioritizes FLAC over other formats
- 🚫 **Live version filtering**: Prefers studio recordings
- 📁 **Auto-path detection**: Finds your Jellyfin directories automatically
- 🔐 **Permission handling**: Sets correct file ownership for Jellyfin
- 📊 **Detailed reporting**: Shows exactly what was found/missing

## 🚀 Quick Start

### Prerequisites

- Python 3.6+
- Jellyfin server with music library
- Playlist exported from Soundiiz, Spotify, or similar (CSV format recommended)

### Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/jellyfin-playlist-generator.git
cd jellyfin-playlist-generator
```

2. Make the script executable:
```bash
chmod +x jellyfin_playlist_generator.py
```

### Usage

1. **Export your playlist** from Soundiiz/Spotify as CSV format

2. **Run the script**:
```bash
python3 jellyfin_playlist_generator.py your_playlist.csv
```

3. **Follow the prompts**:
   - The script will auto-detect your Jellyfin paths (or ask for them)
   - Enter a name for your playlist
   - Watch as it finds your tracks with impressive accuracy!

4. **Scan your Jellyfin library** to make the playlist appear

## 📊 Expected Results

The tool typically achieves **95-100% success rates** on well-organized music libraries:

```
📊 Final results:
✅ Found: 284 tracks
❌ Not found: 1 tracks

🎵 Playlist should now be available in Jellyfin!
```

## 🔧 How It Works

### Multi-Stage Matching

1. **Stage 1 - Strict**: High similarity thresholds for artist and title
2. **Stage 2 - Medium**: Slightly relaxed matching criteria  
3. **Stage 3 - Loose**: Very permissive matching for edge cases

### Interactive Selection

For tracks that automatic matching can't handle:
```
🔍 Interactive search for: Artist - Track Name
    Possible matches:
    [ 1] ✅ 🎵 FLAC 0.85 - Artist - Track Name
         01 - Artist - Track Name.flac
    [ 2] ✅ 🎶 MP3 0.72 - Similar Artist - Similar Track
         05 - Similar Artist - Similar Track.mp3
    Select track (1-2) or 's' to skip: 1
```

### Smart Preferences

- **FLAC > MP3** > other formats
- **Studio recordings > Live versions**
- **Exact matches > fuzzy matches**
- **Artist matching** prevents covers/wrong versions

## 📁 Supported Input Formats

### CSV (Recommended)
```csv
title,artist,album
"Bohemian Rhapsody","Queen","A Night at the Opera"
"Stairway to Heaven","Led Zeppelin","Led Zeppelin IV"
```

### TXT (Simple)
```
Queen - Bohemian Rhapsody
Led Zeppelin - Stairway to Heaven
```

## 🛠️ Configuration

The script auto-detects common Jellyfin paths:

**Music Libraries:**
- `/mnt/datapool/music`
- `/media/music`
- `/var/lib/jellyfin/music`
- `/home/jellyfin/music`

**Playlist Directories:**
- `/var/lib/jellyfin/data/playlists`
- `/config/data/playlists` (Docker)
- `/jellyfin/data/playlists`

## 🐛 Troubleshooting

### Playlist not appearing in Jellyfin?
1. Check file permissions: `ls -la /var/lib/jellyfin/data/playlists/YourPlaylist/`
2. Should show `jellyfin:jellyfin` ownership
3. Scan your music library in Jellyfin Dashboard
4. Restart Jellyfin if needed: `sudo systemctl restart jellyfin`

### Low match rates?
- Ensure your music files follow standard naming: `Artist/Album/Track - Title.ext`
- Check that artist names in playlist match your folder structure
- Use the interactive mode to manually select difficult tracks

### Permission errors?
Run manually: `sudo chown -R jellyfin:jellyfin /var/lib/jellyfin/data/playlists/`

## 🤝 Contributing

Contributions are welcome! This tool was created by the community, for the community.

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with your music library
5. Submit a pull request

## 📄 License

MIT License - feel free to use, modify, and distribute.

## 🙏 Acknowledgments

- Built out of frustration with existing tools
- Inspired by the Jellyfin community's need for better playlist management
- Thanks to everyone who tested and provided feedback

---

**Star this repo if it solved your playlist woes!** ⭐