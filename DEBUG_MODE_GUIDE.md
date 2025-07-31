# Rush Royale Bot - Debug Mode Guide

The Debug Mode provides comprehensive visibility into what the bot sees, what it decides to do, and warns when things don't go according to plan. This guide explains how to enable and use the debug features.

## 🚀 Quick Start

### Enable Debug Mode

**Method 1: Configuration File**
1. Open `config.ini`
2. Set `enabled = True` in the `[debug]` section:
```ini
[debug]
enabled = True
save_screenshots = True
save_grid_states = True
save_unit_crops = True
log_file = debug.log
```

**Method 2: GUI Toggle**
1. Start the bot GUI (`python launch_gui.bat`)
2. Check the "Debug Mode" checkbox in the Options section
3. The setting will be automatically saved to config.ini

## 🔍 What Debug Mode Shows You

### 1. Real-Time Bot Vision
- **Screenshot Analysis**: See exactly what the bot captures from the screen
- **Icon Detection**: View which UI elements the bot recognizes
- **Grid State**: Visual representation of the game board with unit recognition
- **Unit Recognition Confidence**: How certain the bot is about each unit identified

### 2. Decision Making Process
- **Strategy Planning**: See why the bot chooses specific actions
- **Merge Logic**: Understand which units the bot decides to merge and why
- **Priority Systems**: View how the bot prioritizes different actions
- **Alternative Considerations**: See what other options the bot considered

### 3. Action Execution
- **Click Tracking**: Visual annotations showing where the bot clicks
- **Timing Analysis**: How long each operation takes
- **Success/Failure Status**: Whether actions completed as expected
- **Error Recovery**: How the bot handles and recovers from errors

### 4. Performance Monitoring
- **Operation Speed**: Timing for all bot operations
- **Threshold Violations**: Warnings when operations take too long
- **Bottleneck Identification**: Which parts of the bot are slowest
- **Efficiency Metrics**: Overall bot performance statistics

## 📁 Debug Output Files

When debug mode is enabled, the bot creates several types of output files:

### Directory Structure
```
debug_output/
├── screenshots/          # Raw screenshots captured by the bot
├── annotated/           # Screenshots with visual annotations
├── grids/              # Grid state visualizations
├── units/              # Individual unit crop images
debug.log               # Detailed text log of all operations
debug_session_*.json    # Exportable session data
```

### File Types Explained

**Screenshots** (`debug_output/screenshots/`)
- Raw screenshots captured from the device
- Named with timestamps for chronological order
- Useful for understanding what the bot was seeing at specific times

**Annotated Images** (`debug_output/annotated/`)
- Screenshots with visual overlays showing bot actions
- Click points, swipe paths, and UI element detection
- Color-coded for different action types (green=success, red=error)

**Grid Visualizations** (`debug_output/grids/`)
- Visual representation of the game board state
- Shows recognized units with names and ranks
- Empty slots and unrecognized units clearly marked

**Debug Log** (`debug.log`)
- Comprehensive text log of all bot operations
- Timestamped entries with detailed context
- Searchable for specific events or error patterns

## 🖥️ GUI Debug Information

The bot GUI displays real-time debug information when debug mode is enabled:

### Debug Status Panel
- **Debug Enabled**: Current debug mode status
- **Recent Events**: Count of events in the last 5 minutes
- **Warnings**: Number of warnings generated
- **Errors**: Number of errors encountered
- **Event Types**: Breakdown of different operation types
- **Last Operation**: Most recent bot action
- **Grid Units Tracked**: Current game board analysis

### Export Debug Data
Click the "Export Debug" button to create a comprehensive JSON file containing:
- Complete session event log
- Performance metrics
- Error summaries
- Configuration settings used

## 🔧 Debug Configuration Options

### Core Settings
```ini
[debug]
# Master switch for all debug features
enabled = False

# Save screenshots during operations
save_screenshots = True

# Save grid state visualizations
save_grid_states = True

# Save individual unit crop images
save_unit_crops = True

# Debug log file location
log_file = debug.log
```

### Advanced Configuration
You can customize debug behavior by modifying these settings in the debug system:

- **Max Events**: Limit memory usage (default: 1000 events)
- **Update Frequency**: How often GUI updates debug info (default: 2 seconds)
- **Screenshot Quality**: Image compression for debug outputs
- **Log Retention**: How long to keep old debug files

## 📊 Understanding Debug Events

### Event Types

**SCREEN_CAPTURE**
- Screenshot operations and image processing
- File size, resolution, capture time
- Errors in screen capture or image corruption

**UNIT_RECOGNITION**
- Grid analysis and unit identification
- Recognition confidence levels
- Misidentified or unclear units

**ACTION_PLAN**
- Bot decision-making process
- Strategy selection and reasoning
- Alternative actions considered

**ACTION_EXECUTION**
- Click, swipe, and input operations
- Success/failure status
- Timing and coordination

**MERGE_STRATEGY**
- Unit merging logic and planning
- Priority unit handling
- Board state analysis

**PERFORMANCE**
- Operation timing and bottlenecks
- Threshold violations
- Efficiency metrics

**ERROR_RECOVERY**
- Error detection and handling
- Recovery attempts and success rates
- Fallback mechanisms

### Warning Categories

**Recognition Warnings**
- Low confidence unit identification
- Unexpected grid changes
- Missing or corrupt unit images

**Performance Warnings**
- Operations exceeding time thresholds
- Memory usage concerns
- Network connectivity issues

**Strategy Warnings**
- Suboptimal decision making
- Conflicting priorities
- Unusual game states

**System Warnings**
- File system errors
- Configuration problems
- Hardware limitations

## 🐛 Troubleshooting with Debug Mode

### Common Issues and Debug Solutions

**Bot Not Recognizing Units**
1. Enable debug mode
2. Check `debug_output/grids/` for grid visualizations
3. Look for recognition confidence in debug.log
4. Verify unit images in `units/` folder match `all_units/`

**Bot Clicking Wrong Locations**
1. Check `debug_output/annotated/` for click visualizations
2. Review ACTION_EXECUTION events in debug.log
3. Verify screen resolution matches expected values
4. Check for UI scaling issues

**Bot Making Poor Decisions**
1. Review DECISION events in debug.log
2. Check MERGE_STRATEGY events for logic flow
3. Examine grid state visualizations
4. Verify configuration settings match strategy

**Performance Issues**
1. Check PERFORMANCE warnings in debug.log
2. Review operation timing in debug data export
3. Look for bottlenecks in specific operations
4. Monitor system resource usage

### Debug Log Analysis

Search for specific patterns in debug.log:

```bash
# Find all errors
grep "ERROR" debug.log

# Find performance issues
grep "threshold exceeded" debug.log

# Find unit recognition problems
grep "Low confidence" debug.log

# Find strategy warnings
grep "Unexpected" debug.log
```

## 📈 Performance Impact

### Resource Usage
Debug mode increases resource usage:
- **Disk Space**: ~10-50MB per hour (depends on activity)
- **CPU Usage**: ~5-10% additional overhead
- **Memory Usage**: ~50-100MB for event storage
- **Network**: No additional network usage

### Performance Recommendations
- Disable debug mode during extended farming sessions
- Regularly clean old debug files to free disk space
- Monitor system performance if running on low-end hardware
- Use debug mode primarily for troubleshooting and optimization

## 🔒 Privacy and Security

### Data Handling
- Debug files contain screenshots of your game
- No personal information or account details are logged
- All data is stored locally on your system
- No data is transmitted over the network

### File Management
- Debug files can be safely deleted when no longer needed
- Exported JSON files can be shared for troubleshooting (remove personal info first)
- Screenshots may contain game progress information

## 💡 Tips for Effective Debugging

### Best Practices
1. **Enable debug mode only when needed** - Reduces resource usage
2. **Review debug output regularly** - Identify patterns and improvements
3. **Export debug data before major changes** - Helps track improvements
4. **Clean old debug files periodically** - Prevents disk space issues
5. **Use debug mode for new unit configurations** - Verify recognition accuracy

### Advanced Usage
- Combine debug mode with performance monitoring for comprehensive analysis
- Use debug exports to track bot improvement over time
- Share debug data with other users for collaborative troubleshooting
- Create custom analysis scripts using exported JSON data

## 🆘 Getting Help

If you encounter issues with debug mode:

1. **Check the debug.log file** for error messages
2. **Export debug session data** for comprehensive analysis
3. **Review visual debug outputs** for obvious problems
4. **Post debug information** in community forums or issues
5. **Include relevant debug files** when asking for help

Remember: Debug mode is a powerful tool for understanding and improving bot performance. Use it wisely to optimize your Rush Royale Bot experience!
