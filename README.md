# Bible Verse Clock for InkyPi

A beautiful Bible verse display plugin for InkyPi e-ink displays. Shows time-based verses where the hour determines the chapter and minute determines the verse number.

## Features

- 📖 **7 Bible Translations**: NASB, KJV, NIV, ESV, NKJV, NLT, CSB
- 🎨 **4 Layout Styles**: Corner, Center, Left, Right alignment options
- 📏 **3 Size Presets**: Small, Medium, Large text sizes
- 🖼️ **5 Border Styles**: None, Solid, Dashed, Dotted, Double
- 🎨 **Full Color Customization**: Background, verse, reference, translation, and border colors
- 🔤 **4 Font Options**: Jost, Napoli, Dogica, DS-Digital
- 💾 **Offline Support**: Download verses for offline use
- 🕐 **Time-Based Verses**: Hour = chapter, Minute = verse

## Installation

1. SSH into your InkyPi:
```bash
ssh admin@your-inkypi-hostname
```

2. Navigate to the plugins directory:
```bash
cd /usr/local/inkypi/src/plugins
```

3. Clone this repository:
```bash
git clone https://github.com/TheProsumerUser/bible-verse-clock.git bible_verse
```

4. Restart InkyPi:
```bash
sudo systemctl restart inkypi
```

5. Open your browser and go to `http://your-inkypi-hostname.local`

6. The Bible Verse Clock plugin should now appear in your plugin list!

## Usage

1. Click on **Bible Verse Clock** in the plugin list
2. Customize your settings:
   - Choose a translation
   - Select layout style
   - Pick size preset
   - Add borders if desired
   - Customize colors
3. Click **"Add to Playlist"** to save your configuration
4. Go to **Playlists** to activate it

## Offline Download

To use verses offline:

1. In the plugin settings, check the translations you want to download
2. Set **Start Download** to "Yes"
3. Click **"Add to Playlist"**
4. The plugin will download all time-based verses in the background

## Credits

Created with ❤️ for the InkyPi community

## License

MIT License - feel free to use and modify!
