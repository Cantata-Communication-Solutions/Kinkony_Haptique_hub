# Haptique IR/RF Hub - Home Assistant Integration

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/Cantata-Communication-Solutions/haptique_ir_rf_hub)](https://github.com/Cantata-Communication-Solutions/haptique_ir_rf_hub/releases)
[![License](https://img.shields.io/github/license/Cantata-Communication-Solutions/haptique_ir_rf_hub)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Control your IR (Infrared) and RF (433MHz) devices through Home Assistant with the Haptique IR/RF Hub.

## ⚠️ Integration Status

- **Current**: Custom HACS Integration
- **Goal**: Official Home Assistant Integration (in progress)

## 📋 Overview

This custom integration allows you to learn and replay IR and RF commands using your Haptique IR/RF Hub device. Once configured, you can control your appliances, lights, fans, TV, AVR, and other IR/RF devices directly from Home Assistant.

## ✨ Features

- **Learn IR Commands**: Capture infrared remote control signals
- **Learn RF Commands**: Capture 433MHz radio frequency signals
- **Store Commands**: All learned commands are stored in the Hub device
- **Home Assistant Integration**: Use learned commands as entities in automations
- **Easy Management**: Simple Lovelace card interface for learning new commands

## 📦 Prerequisites

- Home Assistant installed and running
- Haptique IR/RF Hub device
- Haptique Config App (to obtain device IP and Token)
- HACS (Home Assistant Community Store) installed

## 🚀 Installation

### Step 1: Install HACS

If you haven't already installed HACS, follow the instructions at [https://hacs.xyz/docs/setup/download](https://hacs.xyz/docs/setup/download)

### Step 2: Add Custom Repository

1. Open Home Assistant
2. Go to **HACS** > **Integrations**
3. Click the **three dots** menu in the top right corner
4. Select **Custom repositories**
5. Add the following repository URL:
   ```
   https://github.com/Cantata-Communication-Solutions/haptique_ir_rf_hub
   ```
6. Select **Integration** as the category
7. Click **Add**

### Step 3: Install the Integration

1. In HACS, search for **"Haptique IR/RF Hub"**
2. Click on it and select **Download**
3. Restart Home Assistant

### Step 4: Add the Device in Haptique Config App

Before adding the integration to Home Assistant, ensure your Haptique IR/RF Hub is set up in the **Haptique Config App**. Note down the following details:
- Device IP Address
- Device Token

### Step 5: Configure in Home Assistant

1. Go to **Settings** > **Devices & Services**
2. Click **+ Add Integration**
3. Search for **"Haptique IR/RF Hub"**
4. Enter your device details:
   - **Device IP**: The IP address from Haptique Config App
   - **Token**: The authentication token from Haptique Config App
5. Click **Submit**

## 🎓 Learning Commands

### Method 1:

Use the link below to open the local learning interface, where you can learn and test IR/RF commands using a simple UI.
Any command you save here will also appear in Home Assistant as an entity.

 
  [http://homeassistant.local:8123/haptique_ir_rf_hub/hub.html](http://homeassistant.local:8123/haptique_ir_rf_hub/hub.html)
 

### Setup Learning Interface

#### 1. Create Lovelace Card

Add the following card to your Lovelace dashboard:

```yaml
type: vertical-stack
cards:
  - type: markdown
    content: |
      ## 📚 Learn IR/RF Commands
      **Steps:**
      1. Point remote at Hub
      2. Press button on remote
      3. Type command name below
      4. **For IR:** Select frame (A, B, C, or D)
      5. Toggle save switch
      
  - type: entities
    title: "🔴 RF Commands (433MHz)"
    entities:
      - input_text.rf_command_name
      - input_boolean.save_rf_trigger
      
  - type: entities
    title: "📡 IR Commands (Infrared)"
    entities:
      - input_text.ir_command_name
      - input_select.ir_frame          # ✅ Add frame selector
      - input_boolean.save_ir_trigger
```

#### 2. Add Configuration

**Step 2a: Update configuration.yaml**

Add the following to your `configuration.yaml` file:

```yaml
input_text:
  rf_command_name:
    name: "RF Command Name"
    max: 50
  ir_command_name:
    name: "IR Command Name"
    max: 50

input_select:
  ir_frame:
    name: "IR Frame"
    options:
      - "A"
      - "B"
      - "C"
      - "D"
    initial: "B"
    icon: mdi:format-list-bulleted

input_boolean:
  save_rf_trigger:
    name: "Save RF Trigger"
    icon: mdi:content-save
  save_ir_trigger:
    name: "Save IR Trigger"
    icon: mdi:content-save

# Make sure this line exists to use automations.yaml file
automation: !include automations.yaml
```

**Step 2b: Add to automations.yaml**

Open your `automations.yaml` file and add these automations:

```yaml
- alias: "Save RF Command"
  mode: single
  trigger:
    - platform: state
      entity_id: input_boolean.save_rf_trigger
      to: "on"
  condition:
    - condition: template
      value_template: "{{ states('input_text.rf_command_name') | length > 0 }}"
  action:
    - service: haptique_ir_rf_hub.save_rf_last
      data:
        name: "{{ states('input_text.rf_command_name') }}"
    - delay: "00:00:00.5"
    - service: persistent_notification.create
      data:
        title: "✅ RF Command Saved"
        message: "Command '{{ states('input_text.rf_command_name') }}' saved!"
    - service: input_text.set_value
      data:
        entity_id: input_text.rf_command_name
        value: ""
    - service: input_boolean.turn_off
      target:
        entity_id: input_boolean.save_rf_trigger

- alias: "Save IR Command"
  mode: single
  trigger:
    - platform: state
      entity_id: input_boolean.save_ir_trigger
      to: "on"
  condition:
    - condition: template
      value_template: "{{ states('input_text.ir_command_name') | length > 0 }}"
  action:
    - service: haptique_ir_rf_hub.save_ir_last
      data:
        name: "{{ states('input_text.ir_command_name') }}"
        frame: "{{ states('input_select.ir_frame') }}"  # ✅ Add frame parameter
    - delay: "00:00:00.5"
    - service: persistent_notification.create
      data:
        title: "✅ IR Command Saved"
        message: "Command '{{ states('input_text.ir_command_name') }}' saved with frame {{ states('input_select.ir_frame') }}!"
    - service: input_text.set_value
      data:
        entity_id: input_text.ir_command_name
        value: ""
    - service: input_boolean.turn_off
      target:
        entity_id: input_boolean.save_ir_trigger
```

**Important Notes:**
- Using `automations.yaml` keeps the GUI automation editor working
- If `automations.yaml` already has content, add these automations to the existing list
- After adding this configuration, restart Home Assistant (Settings > System > Restart)

### How to Learn Commands

#### Learning IR Commands (Infrared)

1. Point your infrared remote at the Haptique Hub
2. Press the button you want to learn
3. In the Lovelace card, enter a name in **"IR Command Name"** field
4. Toggle the **"Save IR Trigger"** switch
5. Wait for the confirmation notification
6. The command is now saved and ready to use

#### Learning RF Commands (433MHz)

1. Point your RF remote at the Haptique Hub
2. Press the button you want to learn
3. In the Lovelace card, enter a name in **"RF Command Name"** field
4. Toggle the **"Save RF Trigger"** switch
5. Wait for the confirmation notification
6. The command is now saved and ready to use

## 💡 Using Learned Commands

Once commands are learned and saved in the Hub, you can use them in multiple ways:

### As Automation Actions

```yaml
automation:
  - alias: "Turn on TV"
    trigger:
      - platform: time
        at: "19:00:00"
    action:
      - service: haptique_ir_rf_hub.send_ir
        data:
          name: "tv_power"
```

### As Button Entities

Learned commands appear as entities in Home Assistant and can be added to your dashboard as buttons or used in scripts.

### In Scripts

```yaml
script:
  movie_mode:
    sequence:
      - service: haptique_ir_rf_hub.send_ir
        data:
          name: "tv_power"
      - delay: "00:00:02"
      - service: haptique_ir_rf_hub.send_ir
        data:
          name: "tv_hdmi_1"
```

## 🔧 Troubleshooting

### Device Not Found
- Ensure the Haptique Hub is powered on and connected to your network
- Verify the IP address hasn't changed (consider setting a static IP)
- Check that the device is added in the Haptique Config App

### Commands Not Learning
- Make sure you're pointing the remote directly at the Hub
- Ensure you enter a command name before toggling the save switch
- Check that the Hub is in learning mode (indicated by LED status)

### Token Issues
- Re-obtain the token from the Haptique Config App -
[![Download on the App Store](https://img.shields.io/badge/Download_on_the-App_Store-black?logo=apple&logoColor=white)](https://apps.apple.com/fr/app/haptique-config/id6639613322?l=en-GB)
[![Get it on Google Play](https://img.shields.io/badge/Get_it_on-Google_Play-green?logo=google-play&logoColor=white)](https://play.google.com/store/apps/details?id=com.cantata.mobile&hl=en_IN)
- Remove and re-add the integration with the new token

## 📝 Support

For issues, questions, or feature requests, please open an issue on [GitHub](https://github.com/Cantata-Communication-Solutions/haptique_ir_rf_hub/issues).

## 📚 Documentation

- [Installation Guide](docs/installation.md)
- [Configuration](docs/configuration.md)
- [API Reference](docs/api-reference.md)
- [Contributing](CONTRIBUTING.md)

## 🧪 For Developers

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Credits

Developed by Cantata Communication Solutions
