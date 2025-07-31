# Wiki Documentation Index

Welcome to the Rush Royale Bot wiki! This documentation provides detailed technical information, troubleshooting guides, and development resources for the new modular architecture.

## 📚 Documentation Structure

### Core Documentation
- **[Technical Guide](Technical-Guide.md)** - Complete system architecture, modular design, and technical details
- **[User Guide](User-Guide.md)** - Comprehensive user documentation and setup instructions
- **[API Reference](API-Reference.md)** - Complete API documentation for developers

### Migration & Updates
- **[GUI Migration Guide](GUI-Migration-Guide.md)** - Legacy to modern GUI migration details
- **[CHANGELOG](CHANGELOG.md)** - Complete version history and release notes

## 🚀 Quick Navigation

### For New Users
- Start with [User Guide](User-Guide.md) for setup and basic usage
- Check the main [README](../README.md) for quick start instructions

### For Developers
- [Technical Guide](Technical-Guide.md) - Understanding the new modular architecture
- [API Reference](API-Reference.md) - Complete API documentation
- Tools documentation in `tools/README.md`

### For Users Upgrading
- [GUI Migration Guide](GUI-Migration-Guide.md) - Migrating from legacy interface
- [CHANGELOG](CHANGELOG.md) - What's new in each version

## 📋 Key Topics

### New Modular Architecture (v2.1.0)
The bot now follows a clean modular design:

**Core Layer (`core/`)**
- `bot.py` - Main bot controller (refactored from legacy bot_core.py)
- `device.py` - Device communication and ADB management
- `perception.py` - Computer vision and unit recognition
- `logger.py` - Centralized logging system  
- `config.py` - Configuration management

**Module Layer (`modules/`)**
- `combat.py` - Combat strategies and battle logic
- `navigation.py` - Game navigation and UI interaction
- `recognition.py` - Advanced unit recognition algorithms
- `automation.py` - Automation workflows and macros
- `debug.py` - Debug utilities and monitoring

**Interface Layer (`interface/`)**
- `gui.py` - Modern graphical interface (refactored from legacy GUI)
- `cli.py` - Command line interface for advanced users

### System Requirements & Setup
- Python 3.13 environment setup
- Bluestacks configuration (1600x900 resolution)
- ADB and device management
- Dependency installation and verification

### Technical Details
- Computer vision pipeline (OpenCV)
- Machine learning rank detection
- Threading and performance optimization
- Device communication patterns

## 🔧 Getting Started

1. **New to the project?** Start with the main [README](../README.md) or [User Guide](User-Guide.md)
2. **Technical details?** See [Technical Guide](Technical-Guide.md) for architecture overview
3. **Development?** Check [API Reference](API-Reference.md) and `tools/README.md`
4. **Issues?** User guides contain troubleshooting sections

## 📖 Documentation Philosophy

This wiki focuses on:
- **Comprehensive technical knowledge** for the new modular architecture
- **Practical guidance** with specific solutions and examples
- **Development resources** for contributors and advanced users
- **Migration information** for users upgrading from older versions

The main README remains focused on quick setup and basic usage.

---

*This documentation reflects the new modular architecture introduced in v2.1.0. Last updated: July 31, 2025*
