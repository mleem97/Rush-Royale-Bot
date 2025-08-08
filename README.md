# RushBot 🎮🤖

| <img width="256" height="256" alt="20250803_2330_RushBot App Logo_simple_compose_01k1rxd9atf21b3v5gkrpyxt0f" src="https://github.com/user-attachments/assets/621d866c-864e-42bb-a28a-c8dca66425a0" /> | A cutting-edge **Python 3.13** reinforcement learning bot for "Rush Royale" that learns game mechanics from scratch through autonomous exploration. Built with hybrid AI architecture combining **Deep Q-Networks (DQN)** for strategic decisions and **Proximal Policy Optimization (PPO)** for real-time combat optimization. This project is planned to push the boundaries of AI in gaming, enabling the bot to adapt, learn, and improve its performance over time without any prior knowledge of the game. |
|------|-------------|

## 🔗 Project History & Related Work

This project builds upon the foundation of several Rush Royale bot implementations:
- **Original Project**: [AxelBjork/Rush-Royale-Bot](https://github.com/AxelBjork/Rush-Royale-Bot) - The pioneering work that started it all
- **Fixed Version**: [mleem97/Rush-Royale-Bot](https://github.com/mleem97/Rush-Royale-Bot) - Improved stability and bug fixes
- **AI Redesign**: [Frikadellental/Rush-Royale-AI](https://github.com/Frikadellental/Rush-Royale-AI) - Complete redesign with modern AI approaches

This repository represents the next evolution, focusing on advanced reinforcement learning techniques and autonomous gameplay.

## 🚀 Features

- **Computer Vision Integration**: Advanced OpenCV-based image recognition for game state analysis
- **Android Device Control**: Direct communication with Android devices via ADB
- **Machine Learning Analytics**: Scikit-learn powered pattern recognition and decision making
- **Real-time Screenshot Processing**: Fast image capture and analysis pipeline
- **Data-Driven Insights**: Comprehensive gameplay analytics and performance tracking
- **Cross-Platform Compatibility**: Works with Android emulators and physical devices
- **Development Tools**: Jupyter notebook integration for analysis and debugging

## 🏗️ Architecture

### Computer Vision Pipeline
- **OpenCV Integration**: Advanced image processing for game state recognition
- **Template Matching**: Precise identification of game elements and UI components
- **Color Analysis**: Strategic decision making based on visual game information
- **Screenshot Processing**: Optimized real-time image capture and analysis

### Machine Learning Components
- **Scikit-learn Models**: Pattern recognition for optimal gameplay strategies  
- **Data Analytics**: Performance tracking and strategic improvement recommendations
- **Feature Extraction**: Automated identification of key game state indicators

### Device Communication
- **ADB Integration**: Direct Android device control and automation
- **Cross-Platform Support**: Compatible with emulators and physical devices
- **Reliable Input Simulation**: Precise touch and gesture automation

## 📋 Requirements

- Python 3.13+
- OpenCV 4.10+
- NumPy 1.24+
- Pandas 2.0+
- Scikit-learn 1.5+
- Pure Python ADB
- Pillow 10.0+
- Matplotlib 3.7+

## 🛠️ Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/rushbot.git
cd rushbot
```

2. Create a virtual environment:
```bash
python -m venv rushbot_env
source rushbot_env/bin/activate  # On Windows: rushbot_env\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## 🎯 Usage

### Training the Bot
```bash
python main.py --mode train --device emulator-5554
```

### Running the Bot
```bash
python main.py --mode play --device 
```

### Analysis Mode
```bash
python analyze.py --log-file gameplay_data.json
```

## 📊 Performance Metrics

The bot tracks various performance indicators:
- Win rate progression over time
- Average game completion time
- Decision accuracy and response time
- Screenshot processing efficiency
- ADB command success rates
- Pattern recognition confidence scores

## 🔧 Configuration

Customize bot behavior through `config.ini`:
```ini
[DEVICE]
device_id = emulator-5554
screenshot_method = adb
resolution = 1920x1080

[GAMEPLAY]
action_delay = 0.5
confidence_threshold = 0.8
max_game_duration = 300

[ANALYSIS]
save_screenshots = true
log_level = INFO
data_retention_days = 30
```

## 📈 Development Progress

The bot development includes:
1. **Setup Phase**: Device connection and screenshot capture implementation
2. **Vision Development**: Template matching and game state recognition
3. **Automation**: Touch input simulation and game interaction
4. **Analytics Integration**: Performance tracking and data analysis
5. **Optimization**: Speed improvements and reliability enhancements

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This bot is created for educational and research purposes. Please ensure compliance with Rush Royale's Terms of Service when using automated tools.

## 🙏 Acknowledgments

- **AxelBjork** for the original Rush Royale bot implementation
- **mleem97** for improving and fixing the original codebase
- **Frikadellental** for the AI-focused redesign and modern approach
- Rush Royale developers for creating an engaging strategic game
- OpenAI and DeepMind for pioneering reinforcement learning techniques
- The open-source community for providing essential ML libraries
