#!/usr/bin/env python3
"""
Jellyfin Playlist Generator
Converts music playlists from various formats (CSV, TXT) into Jellyfin-native XML playlists.

Originally created to solve the limitations of existing playlist import tools.
Supports multi-stage fuzzy matching, FLAC preference, and interactive selection.

Author: MoriarT3a
License: MIT
"""

import os
import sys
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from difflib import SequenceMatcher
import unicodedata

def find_jellyfin_paths():
    """Auto-detect common Jellyfin installation paths"""
    common_music_paths = [
        "/mnt/datapool/music",
        "/media/music", 
        "/var/lib/jellyfin/music",
        "/home/jellyfin/music",
        "/music",
        "/data/music",
        "/srv/music"
    ]
    
    common_playlist_paths = [
        "/var/lib/jellyfin/data/playlists",
        "/config/data/playlists",  # Docker
        "/jellyfin/data/playlists",
        "/home/jellyfin/data/playlists"
    ]
    
    found_music = None
    found_playlists = None
    
    # Find music library
    for path in common_music_paths:
        if os.path.exists(path) and os.path.isdir(path):
            # Check if it contains music folders
            try:
                dirs = [d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))]
                if len(dirs) > 0:  # Has subdirectories (likely artists)
                    found_music = path
                    break
            except PermissionError:
                continue
    
    # Find playlist directory
    for path in common_playlist_paths:
        if os.path.exists(path) and os.path.isdir(path):
            found_playlists = path
            break
    
    return found_music, found_playlists

def get_user_paths():
    """Get paths from user with auto-detection fallback"""
    
    print("🔍 Auto-detecting Jellyfin paths...")
    auto_music, auto_playlists = find_jellyfin_paths()
    
    # Music library path
    if auto_music:
        print(f"✅ Music library found: {auto_music}")
        use_auto = input(f"Use this path? [Y/n]: ").strip().lower()
        if use_auto in ['', 'y', 'yes']:
            music_path = auto_music
        else:
            music_path = input("Enter music library path: ").strip()
    else:
        print("❌ No music library auto-detected")
        music_path = input("Enter music library path (e.g., /mnt/music): ").strip()
    
    # Validate music path
    if not os.path.exists(music_path):
        print(f"❌ Music path does not exist: {music_path}")
        sys.exit(1)
    
    # Playlist path  
    if auto_playlists:
        print(f"✅ Playlist directory found: {auto_playlists}")
        use_auto = input(f"Use this path? [Y/n]: ").strip().lower()
        if use_auto in ['', 'y', 'yes']:
            playlist_path = auto_playlists
        else:
            playlist_path = input("Enter playlist directory path: ").strip()
    else:
        print("❌ No playlist directory auto-detected")
        playlist_path = input("Enter Jellyfin playlist path (e.g., /var/lib/jellyfin/data/playlists): ").strip()
    
    # Validate playlist path
    if not os.path.exists(playlist_path):
        print(f"❌ Playlist path does not exist: {playlist_path}")
        sys.exit(1)
    
    return music_path, playlist_path

def normalize_text(text):
    """Normalisiert Text für besseren Vergleich"""
    if not text:
        return ""
    
    # Unicode normalisieren
    text = unicodedata.normalize('NFKD', text)
    
    # Zu lowercase und Whitespace bereinigen
    text = text.lower().strip()
    
    # Entferne häufige Zusätze in Klammern
    patterns_to_remove = [
        r'\s*\([^)]*remaster[^)]*\)',
        r'\s*\([^)]*remix[^)]*\)',
        r'\s*\([^)]*edit[^)]*\)',
        r'\s*\([^)]*version[^)]*\)',
        r'\s*\([^)]*mix[^)]*\)',
        r'\s*\([^)]*\d{4}[^)]*\)',  # Jahre in Klammern
        r'\s*\[[^\]]*remaster[^\]]*\]',
        r'\s*\[[^\]]*\d{4}[^\]]*\]',  # Jahre in eckigen Klammern
    ]
    
    for pattern in patterns_to_remove:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    
    # Sonderzeichen vereinheitlichen
    replacements = {
        '&': 'and',
        '+': 'and',
        'ä': 'ae', 'ö': 'oe', 'ü': 'ue', 'ß': 'ss',
        'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
        'á': 'a', 'à': 'a', 'â': 'a', 'ã': 'a',
        'í': 'i', 'ì': 'i', 'î': 'i', 'ï': 'i',
        'ó': 'o', 'ò': 'o', 'ô': 'o', 'õ': 'o',
        'ú': 'u', 'ù': 'u', 'û': 'u', 'ü': 'u',
    }
    
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    # Mehrfache Leerzeichen entfernen
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()

def similarity(a, b):
    """Berechnet Ähnlichkeit zwischen zwei Strings (0-1)"""
    return SequenceMatcher(None, normalize_text(a), normalize_text(b)).ratio()

def is_live_version(filename):
    """Prüft ob es sich um eine Live-Version handelt"""
    live_indicators = ['live', 'concert', 'tour', 'festival', 'unplugged', 'acoustic']
    filename_lower = filename.lower()
    
    return any(indicator in filename_lower for indicator in live_indicators)

def find_best_matches(artist, title, music_library_path, min_similarity=0.75, min_artist_sim=0.7, min_title_sim=0.7):
    """Findet die besten Matches für einen Song mit konfigurierbaren Schwellwerten"""
    matches = []
    
    if not os.path.exists(music_library_path):
        print(f"Warnung: Musikbibliothek-Pfad existiert nicht: {music_library_path}")
        return matches
    
    # Normalisiere Suchbegriffe
    search_artist = normalize_text(artist)
    search_title = normalize_text(title)
    
    # Durchsuche nur Ordner mit passendem Artist (viel schneller!)
    for artist_dir in os.listdir(music_library_path):
        artist_path = os.path.join(music_library_path, artist_dir)
        if not os.path.isdir(artist_path):
            continue
            
        # Prüfe Artist-Ähnlichkeit erst
        artist_sim = similarity(search_artist, normalize_text(artist_dir))
        if artist_sim < min_artist_sim:
            continue
            
        # Durchsuche Albums in diesem Artist-Ordner
        for album_dir in os.listdir(artist_path):
            album_path = os.path.join(artist_path, album_dir)
            if not os.path.isdir(album_path):
                continue
                
            # Durchsuche Songs in diesem Album
            for file in os.listdir(album_path):
                if file.lower().endswith(('.mp3', '.flac', '.m4a', '.ogg', '.wav')):
                    full_path = os.path.join(album_path, file)
                    
                    # Extrahiere Title aus Dateiname
                    filename_no_ext = os.path.splitext(file)[0]
                    
                    # Entferne Track-Nummer am Anfang
                    filename_clean = re.sub(r'^\d+\s*[-\.]\s*', '', filename_no_ext)
                    
                    # Versuche Artist - Title Format zu parsen
                    if ' - ' in filename_clean:
                        parts = filename_clean.split(' - ', 1)
                        if len(parts) == 2:
                            file_artist, file_title = parts
                        else:
                            file_artist = artist_dir
                            file_title = filename_clean
                    else:
                        file_artist = artist_dir
                        file_title = filename_clean
                    
                    # Berechne Ähnlichkeiten
                    file_artist_sim = similarity(search_artist, normalize_text(file_artist))
                    title_sim = similarity(search_title, normalize_text(file_title))
                    
                    # Kombinierte Bewertung
                    combined_sim = (artist_sim * 0.6 + file_artist_sim * 0.2 + title_sim * 0.6) / 1.4
                    
                    # Prüfe Schwellwerte
                    if combined_sim >= min_similarity and artist_sim >= min_artist_sim and title_sim >= min_title_sim:
                        is_live = is_live_version(file)
                        
                        # FLAC-Bonus: Bevorzuge .flac Dateien
                        flac_bonus = 0.05 if file.lower().endswith('.flac') else 0.0
                        final_score = combined_sim + flac_bonus
                        
                        matches.append({
                            'path': full_path,
                            'artist': file_artist,
                            'title': file_title,
                            'similarity': final_score,
                            'artist_sim': artist_sim,
                            'title_sim': title_sim,
                            'is_live': is_live,
                            'filename': file,
                            'is_flac': file.lower().endswith('.flac')
                        })
    
    # Sortiere nach: Nicht-Live zuerst, dann FLAC bevorzugt, dann nach Ähnlichkeit
    matches.sort(key=lambda x: (x['is_live'], not x['is_flac'], -x['similarity']))
    
    return matches

def interactive_search(artist, title, music_library_path):
    """Interactive search with user selection"""
    print(f"\n🔍 Interactive search for: {artist} - {title}")
    
    # Very loose search
    matches = find_best_matches(artist, title, music_library_path, 
                              min_similarity=0.3, min_artist_sim=0.2, min_title_sim=0.3)
    
    if not matches:
        print("    ❌ No matches found even with loose search")
        return None
    
    # Show top 10 matches
    print("    Possible matches:")
    for i, match in enumerate(matches[:10], 1):
        status = "🔴 LIVE" if match['is_live'] else "✅"
        format_icon = "🎵 FLAC" if match['is_flac'] else "🎶"
        print(f"    [{i:2d}] {status} {format_icon} {match['similarity']:.2f} - {match['artist']} - {match['title']}")
        print(f"         {match['filename']}")
    
    while True:
        try:
            choice = input(f"    Select track (1-{min(len(matches), 10)}) or 's' to skip: ").strip().lower()
            
            if choice == 's':
                return None
            
            choice_num = int(choice)
            if 1 <= choice_num <= min(len(matches), 10):
                selected_match = matches[choice_num - 1]
                print(f"    ✅ Selected: {selected_match['filename']}")
                return selected_match
            else:
                print(f"    ⚠️  Please enter a number between 1 and {min(len(matches), 10)}")
                
        except ValueError:
            print("    ⚠️  Please enter a valid number or 's' to skip")

def search_with_fallback(artist, title, music_library_path):
    """Mehrstufige Suche mit fallback"""
    
    # Stufe 1: Sehr strikt (ursprünglich)
    matches = find_best_matches(artist, title, music_library_path, 
                              min_similarity=0.75, min_artist_sim=0.7, min_title_sim=0.7)
    if matches:
        return matches[0]  # Bester Match
    
    # Stufe 2: Mittlere Striktheit
    matches = find_best_matches(artist, title, music_library_path, 
                              min_similarity=0.65, min_artist_sim=0.6, min_title_sim=0.6)
    if matches:
        return matches[0]  # Bester Match
    
    # Stufe 3: Lockere Suche
    matches = find_best_matches(artist, title, music_library_path, 
                              min_similarity=0.5, min_artist_sim=0.4, min_title_sim=0.5)
    if matches:
        return matches[0]  # Bester Match
    
    # Nichts gefunden
    return None

def create_jellyfin_playlist(playlist_name, tracks, jellyfin_playlist_path):
    """Erstellt eine Jellyfin-kompatible XML Playlist"""
    
    # Erstelle Playlist-Ordner
    playlist_dir = os.path.join(jellyfin_playlist_path, playlist_name)
    os.makedirs(playlist_dir, exist_ok=True)
    
    # Erstelle XML-Struktur
    root = ET.Element('Item')
    
    # PlaylistItems Container
    playlist_items = ET.SubElement(root, 'PlaylistItems')
    
    for track_path in tracks:
        playlist_item = ET.SubElement(playlist_items, 'PlaylistItem')
        path_elem = ET.SubElement(playlist_item, 'Path')
        path_elem.text = track_path
    
    # Shares (leer)
    ET.SubElement(root, 'Shares')
    
    # MediaType
    media_type = ET.SubElement(root, 'PlaylistMediaType')
    media_type.text = 'Audio'
    
    # XML formatieren und speichern
    xml_str = ET.tostring(root, encoding='unicode')
    
    # XML hübsch formatieren
    from xml.dom import minidom
    dom = minidom.parseString(xml_str)
    pretty_xml = dom.toprettyxml(indent='  ')
    
    # Entferne leere Zeilen
    pretty_xml = '\n'.join([line for line in pretty_xml.split('\n') if line.strip()])
    
    # Speichere Playlist
    playlist_file = os.path.join(playlist_dir, 'playlist.xml')
    with open(playlist_file, 'w', encoding='utf-8') as f:
        f.write(pretty_xml)
    
    # Setze korrekte Berechtigungen für Jellyfin
    try:
        import pwd
        import grp
        
        # Finde jellyfin User und Group IDs
        jellyfin_uid = pwd.getpwnam('jellyfin').pw_uid
        jellyfin_gid = grp.getgrnam('jellyfin').gr_gid
        
        # Setze Besitzer für Ordner und Datei
        os.chown(playlist_dir, jellyfin_uid, jellyfin_gid)
        os.chown(playlist_file, jellyfin_uid, jellyfin_gid)
        
        # Setze Berechtigungen
        os.chmod(playlist_dir, 0o755)  # drwxr-xr-x
        os.chmod(playlist_file, 0o644)  # -rw-r--r--
        
        print(f"✅ Permissions set: jellyfin:jellyfin")
        
    except (KeyError, PermissionError) as e:
        print(f"⚠️  Could not set permissions automatically: {e}")
        print(f"💡 Run manually: sudo chown -R jellyfin:jellyfin '{playlist_dir}'")
    
    return playlist_file

def read_playlist(file_path):
    """Liest eine Playlist aus verschiedenen Formaten"""
    tracks = []
    
    # Debug-Ausgabe entfernen für saubere Ausgabe
    # CSV mit pandas-ähnlicher Logik
    if file_path.lower().endswith('.csv'):
        try:
            import csv
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    # Versuche verschiedene Spaltennamen
                    artist = None
                    title = None
                    
                    # Artist finden
                    for col in ['artist', 'Artist', 'ARTIST', 'creator', 'Creator']:
                        if col in row and row[col]:
                            artist = row[col].strip()
                            break
                    
                    # Title finden  
                    for col in ['title', 'Title', 'TITLE', 'track', 'Track', 'song', 'Song']:
                        if col in row and row[col]:
                            title = row[col].strip()
                            break
                    
                    if artist and title:
                        tracks.append((artist, title))
            
            return tracks
        except Exception as e:
            print(f"⚠️  CSV-Parsing fehlgeschlagen: {e}")
    
    # Fallback: Textformat
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Plain text format (Artist - Track)
    for line in content.strip().split('\n'):
        line = line.strip()
        if line and ' - ' in line:
            parts = line.split(' - ', 1)
            if len(parts) == 2:
                artist, track = parts
                tracks.append((artist.strip(), track.strip()))
    
    return tracks

def main():
    print("🎵 Jellyfin Playlist Generator")
    print("=" * 50)
    print("Converts playlists to Jellyfin-native XML format")
    print("Supports CSV and TXT formats with intelligent matching\n")
    
    # Get paths (auto-detect or user input)
    MUSIC_LIBRARY_PATH, JELLYFIN_PLAYLIST_PATH = get_user_paths()
    
    print(f"\n📁 Using paths:")
    print(f"   Music Library: {MUSIC_LIBRARY_PATH}")
    print(f"   Playlists: {JELLYFIN_PLAYLIST_PATH}")
    
    # Playlist file input
    if len(sys.argv) != 2:
        print(f"\nUsage: python3 {sys.argv[0]} <playlist_file>")
        print("Supported formats: .csv, .txt")
        print("Example: python3 jellyfin_playlist_generator.py my_playlist.csv")
        sys.exit(1)
    
    playlist_file = sys.argv[1]
    
    if not os.path.exists(playlist_file):
        print(f"❌ Playlist file not found: {playlist_file}")
        sys.exit(1)
    
    print(f"\n📁 Loading playlist: {playlist_file}")
    tracks = read_playlist(playlist_file)
    
    if not tracks:
        print("❌ No tracks found in playlist!")
        sys.exit(1)
    
    print(f"✅ Found {len(tracks)} tracks")
    
    # Playlist name input
    playlist_name = input("\n🎯 Enter playlist name: ").strip()
    if not playlist_name:
        print("❌ Playlist name cannot be empty!")
        sys.exit(1)
    
    print(f"\n🔍 Searching tracks in music library...")
    
    found_tracks = []
    not_found_first_round = []
    
    # First round: Automatic search with fallback
    for i, (artist, title) in enumerate(tracks, 1):
        print(f"[{i:3d}/{len(tracks)}] {artist} - {title}")
        
        match = search_with_fallback(artist, title, MUSIC_LIBRARY_PATH)
        
        if match:
            found_tracks.append(match['path'])
            status = "🔴 LIVE" if match['is_live'] else "✅"
            format_icon = "🎵 FLAC" if match['is_flac'] else "🎶"
            print(f"    {status} {format_icon} {match['similarity']:.2f} - {match['filename']}")
        else:
            not_found_first_round.append((artist, title))
            print(f"    ❌ Not found")
    
    print(f"\n📊 First round results:")
    print(f"✅ Found: {len(found_tracks)} tracks")
    print(f"❌ Not found: {len(not_found_first_round)} tracks")
    
    # Second round: Interactive search for missing tracks
    final_not_found = []
    if not_found_first_round:
        print(f"\n🔍 Interactive search for {len(not_found_first_round)} missing tracks...")
        print("💡 You can select from a list or skip ('s') for each track")
        
        interactive_found = []
        
        for artist, title in not_found_first_round:
            match = interactive_search(artist, title, MUSIC_LIBRARY_PATH)
            if match:
                found_tracks.append(match['path'])
                interactive_found.append((artist, title))
            else:
                final_not_found.append((artist, title))
        
        print(f"\n📊 Interactive search results:")
        print(f"✅ Additionally found: {len(interactive_found)} tracks")
        print(f"❌ Still not found: {len(final_not_found)} tracks")
    else:
        final_not_found = []
    
    print(f"\n📊 Final results:")
    print(f"✅ Found: {len(found_tracks)} tracks")
    print(f"❌ Not found: {len(final_not_found)} tracks")
    
    if final_not_found:
        print(f"\n🔍 Missing tracks:")
        for artist, title in final_not_found:
            print(f"   • {artist} - {title}")
    
    if found_tracks:
        print(f"\n💾 Creating Jellyfin playlist...")
        
        try:
            playlist_file = create_jellyfin_playlist(playlist_name, found_tracks, JELLYFIN_PLAYLIST_PATH)
            print(f"✅ Playlist created: {playlist_file}")
            print(f"📁 Playlist folder: {os.path.dirname(playlist_file)}")
            print(f"\n🎵 Playlist should now be available in Jellyfin!")
            print(f"💡 Tip: Scan your music library in Jellyfin to make it appear")
            
            # Tip for images
            print(f"\n💡 Optional: Add cover images by placing backdrop.webp and folder.webp")
            print(f"   in the folder: {os.path.dirname(playlist_file)}")
            
        except Exception as e:
            print(f"❌ Error creating playlist: {e}")
            sys.exit(1)
    else:
        print("❌ No tracks found - playlist not created")

if __name__ == "__main__":
    main()
