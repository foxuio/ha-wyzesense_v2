# 🧠 WyzeSense V2 for Home Assistant (2025 Core Compatible)

This is a revived and fully functional version of the original [kevinvincent/ha-wyzesense](https://github.com/kevinvincent/ha-wyzesense), now updated and tested to work on **Home Assistant Core 2025.5.1**.

> 🛠️ Designed for WyzeSense V1 USB bridges and motion/contact sensors.

---

## ✨ Features

- 🔄 Works with latest HA Core (async-compatible)
- 🚪 Motion & Door/Window sensors supported
- 🧠 Automatic entity restoration
- 🧾 Persistent notification when sensors are scanned
- 🚫 Prevents duplicated entities using `unique_id` check
- 💾 Local storage support with `.storage/wyzesense`
- 🔄 Works with Sensors V1 y V2
- 🔄 It also works with V1 sensors without MacAddress, which lost their mac due to battery failure.

---

## 📦 Installation

Manually

1. Copy this repo to your Home Assistant config folder under:

<config>/custom_components/wyzesense/yaml

2. Reboot Home Assistant.

---

Option 2:
🧩 HACS Installation (Custom Repository)
If you want to install this integration via HACS, follow these steps:

📦 Step-by-step:
In Home Assistant, go to HACS → Integrations.

Click the three-dot menu (⋮) in the top right.

Select "Custom repositories".

In the Repository URL, enter:

https://github.com/foxuio/ha-wyzesense_v2

In Category, select:
Integration

Click "Add".

Now, search for WyzeSense V2 in HACS and install it.

## ⚙️ Configuration

In your `configuration.yaml`:

```yaml
binary_sensor:
  - platform: wyzesense
    device: auto    ## auto is for autodetect usb port
## or 
binary_sensor:
  - platform: wyzesense
    device: /dev/hidraw0  ## <--- here is your USB port Hub has inserted, check on hardware details 
```
---

##  🔍 Adding Sensors
Navigate to Developer Tools → Services

Call the service: wyzesense.scan

Trigger the sensor (open/close or move near it)

A notification will confirm detection

Entities will be created automatically (e.g., binary_sensor.wyzesense_XXXX).

🧼 Removing Sensors
(Coming soon — service wyzesense.remove under development)

👥 Credits
Original author: kevinvincent

Revival & HA 2025+ compatibility: foxuio (Chris) 🎉

💡 Notes
Compatible with Home Assistant Core 2025.5.1 and newer

Tested on supervised and Home Assistant OS

If you manually remove a sensor from .storage, make sure to clear it from entity registry too


---

## 🍺 Support This Project

If you found this integration useful and want to say thanks...

[![Buy Me a Beer](https://img.shields.io/badge/Buy%20me%20a%20beer-ffdd00?style=for-the-badge&logo=buymeacoffee&logoColor=black)](https://www.buymeacoffee.com/foxuio)


Or just star ⭐ the repo and share it with others who still use WyzeSense!

---
