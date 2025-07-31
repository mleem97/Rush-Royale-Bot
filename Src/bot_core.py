import os
import time
import numpy as np
import pandas as pd
import logging
import configparser
from subprocess import Popen, DEVNULL
# Suppress harmless warnings
import warnings
warnings.filterwarnings("ignore", message="pkg_resources is deprecated", category=UserWarning)
# Android ADB
from scrcpy import Client, const
# Image processing
import cv2
# internal
import bot_perception
import port_scan
from performance_monitor import get_performance_monitor, time_function
from error_recovery import get_error_recovery_system, with_error_recovery
from debug_system import get_debug_system

SLEEP_DELAY = 0.1


class Bot:

    def __init__(self, device=None):
        self.bot_stop = False
        self.combat = self.output = self.grid_df = self.unit_series = self.merge_series = self.df_groups = self.info = self.combat_step = None
        self.logger = logging.getLogger('__main__')
        
        # Initialize debug system
        self.debug = get_debug_system()
        
        # Load configuration for debug settings
        config = configparser.ConfigParser()
        config.read('config.ini')
        if 'debug' in config:
            debug_enabled = config.getboolean('debug', 'enabled', fallback=False)
            self.debug.set_enabled(debug_enabled)
            self.debug.save_screenshots = config.getboolean('debug', 'save_screenshots', fallback=True)
            self.debug.save_grid_states = config.getboolean('debug', 'save_grid_states', fallback=True)
            self.debug.save_unit_crops = config.getboolean('debug', 'save_unit_crops', fallback=True)
            if debug_enabled:
                self.logger.info("DEBUG MODE ENABLED - Detailed logging and visualization active")
        
        # Store config for later use
        self.config = config
        
        # Initialize error recovery system
        self.error_recovery = get_error_recovery_system()
        self.error_recovery.logger = self.logger
        
        if device is None:
            device = port_scan.get_device()
        if not device:
            raise Exception("No device found!")
        self.device = device
        self.bot_id = self.device.split(':')[-1]
        self.shell(f'.scrcpy\\adb connect {self.device}')
        # Try to launch application through ADB shell
        self.shell('monkey -p com.my.defense 1')
        # Check if 'bot_feed.png' exists
        if not os.path.isfile(f'bot_feed_{self.bot_id}.png'):
            try:
                self.getScreen()
            except Exception as e:
                self.logger.warning(f"Initial screenshot failed: {e}")
                # Continue initialization - we'll try again later
        self.screenRGB = cv2.imread(f'bot_feed_{self.bot_id}.png')
        self.client = Client(device=self.device)
        # Start scrcpy client
        self.client.start(threaded=True)
        self.logger.info('Connecting to Bluestacks')
        time.sleep(0.5)
        # Turn off video stream (spammy)
        self.client.alive = False

    def __exit__(self, exc_type, exc_value, traceback):
        self.bot_stop = True
        self.logger.info('Exiting bot')
        self.client.stop()

    # Function to send ADB shell command
    def shell(self, cmd):
        p = Popen([".scrcpy\\adb", '-s', self.device, 'shell', cmd], stdout=DEVNULL, stderr=DEVNULL)
        p.wait()

    # Send ADB to click screen
    def click(self, x, y, delay_mult=1):
        # Debug the click action
        self.debug.debug_action_plan(self, 'click', {
            'position': [x, y],
            'delay_multiplier': delay_mult,
            'coordinates': f"({x}, {y})"
        }, expected_outcome="UI element activated")
        
        start_time = time.time()
        success = True
        
        try:
            self.client.control.touch(x, y, const.ACTION_DOWN)
            time.sleep(SLEEP_DELAY / 2 * delay_mult)
            self.client.control.touch(x, y, const.ACTION_UP)
            time.sleep(SLEEP_DELAY * delay_mult)
            
            self.debug.log_event("ACTION", "click_executed", {
                'position': [x, y],
                'delay_mult': delay_mult,
                'duration': time.time() - start_time
            })
            
        except Exception as e:
            success = False
            self.logger.error(f"Click failed at ({x}, {y}): {e}")
            self.debug.log_event("ACTION", "click_failed", {
                'position': [x, y],
                'error': str(e)
            }, success=False, warnings=[f"Click failed: {e}"])
            raise
        
        finally:
            # Debug action execution with current screen if available
            img = getattr(self, 'screenRGB', None)
            self.debug.debug_action_execution(self, 'click', success, 
                                            actual_outcome="click_completed", img=img)

    # Click button coords offset and extra delay
    def click_button(self, pos):
        coords = np.array(pos) + 10
        self.click(*coords)
        time.sleep(SLEEP_DELAY * 10)

    # Swipe on combat grid to merge units
    def swipe(self, start, end):
        boxes, box_size = get_grid()
        # Offset from box edge
        offset = 60
        self.client.control.swipe(*boxes[start[0], start[1]] + offset, *boxes[end[0], end[1]] + offset, 20, 1 / 60)

    # Send key command, see py-scrcpy consts
    def key_input(self, key):
        self.client.control.keycode(key)

    # Force restart the game through ADC, or spam 10 disconnects to abandon match
    def restart_RR(self, quick_disconnect=False):
        if quick_disconnect:
            for i in range(15):
                self.shell('monkey -p com.my.defense 1')  # disconnects really quick for unknown reasons
            return
        # Force kill game through ADB shell
        self.shell('am force-stop com.my.defense')
        time.sleep(2)
        # Launch application through ADB shell
        self.shell('monkey -p com.my.defense 1')
        time.sleep(10)  # wait for app to load

    # Take screenshot of device screen and load pixel values
    @time_function('screen_capture')
    def getScreen(self):
        start_time = time.time()
        success = False
        img = None
        
        try:
            bot_id = self.device.split(':')[-1]
            screenshot_path = f'bot_feed_{bot_id}.png'
            
            self.debug.log_event("SCREEN_CAPTURE", "starting_capture", {
                'device': self.device,
                'screenshot_path': screenshot_path
            })
            
            # Use ADB shell screencap command with proper output redirection
            cmd = ['.scrcpy\\adb', '-s', self.device, 'exec-out', 'screencap', '-p']
            
            # Execute command and save output to file
            with open(screenshot_path, 'wb') as f:
                p = Popen(cmd, stdout=f, stderr=DEVNULL)
                p.wait()
            
            # Verify file exists and is valid
            if not os.path.exists(screenshot_path):
                raise FileNotFoundError(f"Screenshot file not created: {screenshot_path}")
                
            # Load screenshot and verify it's valid
            new_img = cv2.imread(screenshot_path)
            if new_img is None:
                raise ValueError(f"Invalid screenshot data in: {screenshot_path}")
            
            # Check if image has reasonable dimensions
            if new_img.shape[0] < 100 or new_img.shape[1] < 100:
                raise ValueError(f"Screenshot too small: {new_img.shape}")
                
            self.screenRGB = new_img
            img = new_img
            success = True
            
            self.debug.log_event("SCREEN_CAPTURE", "capture_success", {
                'image_shape': new_img.shape,
                'file_size': os.path.getsize(screenshot_path),
                'duration': time.time() - start_time
            })
            
            self.logger.debug(f"Screenshot captured: {new_img.shape}")
            
        except Exception as e:
            self.logger.error(f"Screenshot capture failed: {e}")
            
            self.debug.log_event("SCREEN_CAPTURE", "capture_failed", {
                'error': str(e),
                'error_type': type(e).__name__,
                'duration': time.time() - start_time
            }, success=False, warnings=[str(e)])
            
            # Try error recovery
            if hasattr(self, 'error_recovery'):
                try:
                    recovery_success = self.error_recovery.handle_error(e, 'screen_capture')
                    if recovery_success:
                        # Try to load the recovered screenshot
                        bot_id = self.device.split(':')[-1]
                        screenshot_path = f'bot_feed_{bot_id}.png'
                        if os.path.exists(screenshot_path):
                            new_img = cv2.imread(screenshot_path)
                            if new_img is not None and new_img.shape[0] > 100 and new_img.shape[1] > 100:
                                self.screenRGB = new_img
                                img = new_img
                                success = True
                                self.debug.debug_error_recovery(self, e, "recovered_screenshot", True)
                                self.logger.info("Screenshot recovery successful")
                                return
                except Exception as recovery_error:
                    self.logger.warning(f"Screenshot recovery failed: {recovery_error}")
                    self.debug.debug_error_recovery(self, e, "screenshot_recovery_failed", False)
            
            # Try fallback: use existing screenshot if available
            bot_id = self.device.split(':')[-1]
            fallback_path = f'bot_feed_{bot_id}.png'
            if os.path.exists(fallback_path) and hasattr(self, 'screenRGB') and self.screenRGB is not None:
                self.logger.warning("Using cached screenshot due to capture failure")
                self.debug.log_event("SCREEN_CAPTURE", "using_cached", {
                    'fallback_path': fallback_path
                }, warnings=["Using cached screenshot - may be outdated"])
                return
            else:
                raise FileNotFoundError(f"Screenshot capture failed: bot_feed_{bot_id}.png")
        
        finally:
            # Always debug the screen capture result
            self.debug.debug_screen_capture(self, success, img)

    # Crop latest screenshot taken
    def crop_img(self, x, y, dx, dy, name='icon.png'):
        # Load screen
        img_rgb = self.screenRGB
        img_rgb = img_rgb[y:y + dy, x:x + dx]
        cv2.imwrite(name, img_rgb)

    def getMana(self):
        return int(self.getText(220, 1360, 90, 50, new=False, digits=True))

    # find icon on screen
    def getXYByImage(self, target, new=True):
        valid_targets = ['battle_icon', 'pvp_button', 'back_button', 'cont_button', 'fighting']
        if not target in valid_targets:
            return "INVALID TARGET"
        if new:
            self.getScreen()
        imgSrc = f'icons/{target}.png'
        img_rgb = self.screenRGB
        img_gray = cv2.cvtColor(img_rgb, cv2.COLOR_BGR2GRAY)
        template = cv2.imread(imgSrc, 0)
        res = cv2.matchTemplate(img_gray, template, cv2.TM_CCOEFF_NORMED)
        threshold = 0.8
        loc = np.where(res >= threshold)
        if len(loc[0]) > 0:
            y = loc[0][0]
            x = loc[1][0]
            return [x, y]

    def get_store_state(self):
        x, y = [140, 1412]
        store_states_names = ['refresh', 'new_store', 'nothing', 'new_offer', 'spin_only']
        store_states = np.array([[255, 255, 255], [27, 235, 206], [63, 38, 12], [48, 253, 251], [80, 153, 193]])
        store_rgb = self.screenRGB[y:y + 1, x:x + 1]
        store_rgb = store_rgb[0][0]
        # Take mean square of rgb value and store states
        store_mse = ((store_states - store_rgb)**2).mean(axis=1)
        closest_state = store_mse.argmin()
        return store_states_names[closest_state]

    # Check if any icons are on screen
    def get_current_icons(self, new=True, available=False):
        current_icons = []
        # Update screen and load screenshot as grayscale
        if new:
            self.getScreen()
        img_rgb = self.screenRGB
        img_gray = cv2.cvtColor(img_rgb, cv2.COLOR_BGR2GRAY)
        # Check every target in dir
        for target in os.listdir("icons"):
            x = 0  # reset position
            y = 0
            # Load icon
            imgSrc = f'icons/{target}'
            template = cv2.imread(imgSrc, 0)
            # Compare images
            res = cv2.matchTemplate(img_gray, template, cv2.TM_CCOEFF_NORMED)
            threshold = 0.8
            loc = np.where(res >= threshold)
            icon_found = len(loc[0]) > 0
            if icon_found:
                y = loc[0][0]
                x = loc[1][0]
            current_icons.append([target, icon_found, (x, y)])
        icon_df = pd.DataFrame(current_icons, columns=['icon', 'available', 'pos [X,Y]'])
        # filter out only available buttons
        if available:
            icon_df = icon_df[icon_df['available'] == True].reset_index(drop=True)
        return icon_df

    # Scan battle grid, update OCR images
    def scan_grid(self, new=False):
        boxes, box_size = get_grid()
        # should be enabled by default
        if new:
            self.getScreen()
        box_list = boxes.reshape(15, 2)
        names = []
        if not os.path.isdir('OCR_inputs'):
            os.mkdir('OCR_inputs')
        for i in range(len(box_list)):
            file_name = f'OCR_inputs/icon_{str(i)}.png'
            self.crop_img(*box_list[i], *box_size, name=file_name)
            names.append(file_name)
        return names

    # Take random unit in series, find corresponding dataframe and merge two random ones
    def merge_unit(self, df_split, merge_series):
        # Pick a random filtered target
        if len(merge_series) > 0:
            merge_target = merge_series.sample().index[0]
        else:
            return merge_series
        # Collect unit dataframe
        merge_df = df_split.get_group(merge_target)
        if len(merge_df) > 1:
            merge_df = merge_df.sample(n=2)
        else:
            return merge_df
        self.log_merge(merge_df)
        # Extract unit position from dataframe
        unit_chosen = merge_df['grid_pos'].tolist()
        # Send Merge
        self.swipe(*unit_chosen)
        time.sleep(0.2)
        return merge_df

    # Merge special units ['harlequin.png','dryad.png','mime.png','scrapper.png']
    # Add logging event
    def merge_special_unit(self, df_split, merge_series, special_type):
        # Get special merge unit
        special_unit, normal_unit = [
            adv_filter_keys(merge_series, units=special_type, remove=remove) for remove in [False, True]
        ]  # scrapper support not tested
        # Get corresponding dataframes
        special_df, normal_df = [df_split.get_group(unit.index[0]).sample() for unit in [special_unit, normal_unit]]
        merge_df = pd.concat([special_df, normal_df])
        self.log_merge(merge_df)
        # Merge 'em
        unit_chosen = merge_df['grid_pos'].tolist()
        self.swipe(*unit_chosen)
        time.sleep(0.2)
        return merge_df

    def log_merge(self, merge_df):
        merge_df['unit'] = merge_df['unit'].apply(lambda x: x.replace('.png', ''))
        unit1, unit2 = merge_df.iloc[0:2]['unit']
        rank = merge_df.iloc[0]['rank']
        log_msg = f"Rank {rank} {unit1}-> {unit2}"
        # Determine log level from rank
        if rank > 4:
            self.logger.error(log_msg)
        elif rank > 2:
            self.logger.debug(log_msg)
        else:
            self.logger.info(log_msg)

    # Find targets for special merge
    def special_merge(self, df_split, merge_series, target='zealot.png'):
        merge_df = None
        # Try to rank up dryads
        dryads_series = adv_filter_keys(merge_series, units='dryad.png')
        if not dryads_series.empty:
            dryads_rank = dryads_series.index.get_level_values('rank')
            for rank in dryads_rank:
                merge_series_dryad = adv_filter_keys(merge_series, units=['harlequin.png', 'dryad.png'], ranks=rank)
                merge_series_zealot = adv_filter_keys(merge_series, units=['dryad.png', target], ranks=rank)
                if len(merge_series_dryad.index) == 2:
                    merge_df = self.merge_special_unit(df_split, merge_series_dryad, special_type='harlequin.png')
                    break
                if len(merge_series_zealot.index) == 2:
                    merge_df = self.merge_special_unit(df_split, merge_series_zealot, special_type='dryad.png')
                    break
        return merge_df

    # Harley Merge target
    def harley_merge(self, df_split, merge_series, target='knight_statue.png'):
        merge_df = None
        # Try to copy target
        hq_series = adv_filter_keys(merge_series, units='harlequin.png')
        if not hq_series.empty:
            hq_rank = hq_series.index.get_level_values('rank')
            for rank in hq_rank:
                merge_series_target = adv_filter_keys(merge_series, units=['harlequin.png', target], ranks=rank)
                if len(merge_series_target.index) == 2:
                    merge_df = self.merge_special_unit(df_split, merge_series_target, special_type='harlequin.png')
                    break
        return merge_df

    # Try to find a merge target and merge it
    def try_merge(self, rank=1, prev_grid=None, merge_target='zealot.png'):
        start_time = time.time()
        info = ''
        merge_df = None
        
        # Debug the merge planning
        self.debug.debug_decision_making(self, {
            'rank': rank,
            'merge_target': merge_target,
            'has_previous_grid': prev_grid is not None
        }, 'try_merge', f"Attempting to merge units targeting {merge_target}")
        
        # Scan grid and get unit status
        names = self.scan_grid(new=False)
        grid_df = bot_perception.grid_status(names, prev_grid=prev_grid)
        
        # Debug unit recognition results
        self.debug.debug_unit_recognition(self, grid_df, getattr(self, 'screenRGB', None))
        
        # Log detailed grid analysis
        recognized_units = grid_df[grid_df['unit'] != 'empty.png']
        empty_slots = grid_df[grid_df['unit'] == 'empty.png']
        
        self.debug.log_event("GRID_ANALYSIS", "unit_scan_complete", {
            'total_positions': len(grid_df),
            'recognized_units': len(recognized_units),
            'empty_slots': len(empty_slots),
            'target_unit_count': len(grid_df[grid_df['unit'] == merge_target]),
            'unit_types': grid_df['unit'].value_counts().to_dict(),
            'average_rank': grid_df[grid_df['rank'] > 0]['rank'].mean() if len(grid_df[grid_df['rank'] > 0]) > 0 else 0
        })
        
        df_split, unit_series, df_groups, group_keys = grid_meta_info(grid_df)
        # Select stuff to merge
        merge_series = unit_series.copy()
        # Remove empty groups
        merge_series = adv_filter_keys(merge_series, units='empty.png', remove=True)
        
        # Debug merge strategy
        merge_candidates = sum(merge_series)
        self.debug.log_event("MERGE_STRATEGY", "planning_merges", {
            'total_merge_candidates': merge_candidates,
            'merge_target': merge_target,
            'merge_series_summary': {k: v for k, v in zip(merge_series.index, merge_series.values) if v > 0}
        })
        
        # Do special merge with dryad/Harley
        self.special_merge(df_split, merge_series, merge_target)
        # Use harely on high dps targets
        if merge_target == 'demon_hunter.png':
            self.harley_merge(df_split, merge_series, target=merge_target)
            # Remove all demons (for co-op)
            demons = adv_filter_keys(merge_series, units='demon_hunter.png')
            num_demon = sum(demons)
            if num_demon >= 11:
                # If board is mostly demons, chill out
                self.logger.info(f'Board is full of demons, waiting...')
                self.debug.log_event("STRATEGY", "demon_overload", {
                    'demon_count': num_demon,
                    'action': 'waiting'
                }, warnings=["Board full of demons - pausing merges"])
                time.sleep(10)
            if self.config.getboolean('bot', 'require_shaman'):
                merge_series = adv_filter_keys(merge_series, units='demon_hunter.png', remove=True)
        merge_series = preserve_unit(merge_series, target='chemist.png')
        # Remove 4x cauldrons
        for _ in range(4):
            merge_series = preserve_unit(merge_series, target='cauldron.png', keep_min=True)
        # Try to keep knight_statue numbers even (can conflict if special_merge already merged)
        num_knight = sum(adv_filter_keys(merge_series, units='knight_statue.png'))
        if num_knight % 2 == 1:
            self.harley_merge(df_split, merge_series, target='knight_statue.png')
        # Preserve 2 highest knight statues
        for _ in range(2):
            merge_series = preserve_unit(merge_series, target='knight_statue.png')
        # Select stuff to merge
        merge_series = merge_series[merge_series >= 2]  # At least 2 units
        merge_series = adv_filter_keys(merge_series, ranks=7, remove=True)  # Remove max ranks
        # Try to merge high priority units
        merge_prio = adv_filter_keys(merge_series,
                                     units=['chemist.png', 'bombardier.png', 'summoner.png', 'knight_statue.png'])
        if not merge_prio.empty:
            info = 'Merging High Priority!'
            self.debug.log_event("MERGE_DECISION", "high_priority_merge", {
                'priority_units': merge_prio.to_dict()
            })
            merge_df = self.merge_unit(df_split, merge_prio)
        # Merge if board is getting full
        if df_groups['empty.png'] <= 2:
            info = 'Merging!'
            self.debug.log_event("MERGE_DECISION", "board_full_merge", {
                'empty_slots': df_groups['empty.png'],
                'reason': 'Board getting full'
            })
            # Add criteria
            low_series = adv_filter_keys(merge_series, ranks=rank, remove=False)
            if not low_series.empty:
                merge_df = self.merge_unit(df_split, low_series)
            else:
                # If grid seems full, merge more units
                info = 'Merging high level!'
                self.debug.log_event("MERGE_DECISION", "forced_high_level_merge", {
                    'reason': 'No low level units available, board full'
                }, warnings=["Forced to merge high level units"])
                merge_series = adv_filter_keys(merge_series,
                                               ranks=[3, 4, 5, 6, 7],
                                               units=['zealot.png', 'crystal.png', 'bruser.png', merge_target],
                                               remove=True)
                if not merge_series.empty:
                    merge_df = self.merge_unit(df_split, merge_series)
        else:
            info = 'need more units!'
            self.debug.log_event("MERGE_DECISION", "no_merge_needed", {
                'empty_slots': df_groups['empty.png'],
                'reason': 'Board has space, spawning more units'
            })
        
        # Final merge execution summary
        duration = time.time() - start_time
        self.debug.log_event("MERGE_EXECUTION", "merge_complete", {
            'merge_info': info,
            'execution_time': duration,
            'merge_performed': merge_df is not None
        })
        
        return grid_df, unit_series, merge_series, merge_df, info

    # Mana level cards
    def mana_level(self, cards, hero_power=False):
        upgrade_pos_dict = {1: [100, 1500], 2: [200, 1500], 3: [350, 1500], 4: [500, 1500], 5: [650, 1500]}
        # Level each card
        for card in cards:
            self.click(*upgrade_pos_dict[card])
        if hero_power:
            self.click(800, 1500)

    # Start a dungeon floor from PvE page
    def play_dungeon(self, floor=5):
        self.logger.debug(f'Starting Dungeon floor {floor}')
        
        # Debug the dungeon selection process
        self.debug.log_event("DUNGEON_START", "play_dungeon_called", {
            'target_floor': floor,
            'chapter_calculation': int(np.ceil((floor)/3))
        })
        
        # Divide by 3 and take ceiling of floor as int
        target_chapter = f'chapter_{int(np.ceil((floor)/3))}.png'
        next_chapter = f'chapter_{int(np.ceil((floor+1)/3))}.png'
        pos = np.array([0, 0])
        avail_buttons = self.get_current_icons(available=True)
        
        # Debug current screen state
        detected_icons = avail_buttons['icon'].tolist() if not avail_buttons.empty else []
        self.debug.log_event("DUNGEON_START", "initial_screen_scan", {
            'icons_detected': detected_icons,
            'looking_for_chapter': target_chapter,
            'dungeon_page_found': (avail_buttons == 'dungeon_page.png').any(axis=None) if not avail_buttons.empty else False
        })
        
        # Check if on dungeon page
        if (avail_buttons == 'dungeon_page.png').any(axis=None):
            self.logger.info(f'Found dungeon page, looking for chapter {target_chapter}')
            
            # Swipe to the top
            [self.swipe([0, 0], [2, 0]) for i in range(14)]
            self.click(30, 600, 5)  # stop scroll and scan screen for buttons
            
            # Keep swiping until floor is found
            expanded = 0
            chapter_found = False
            
            for i in range(10):
                # Scan screen for buttons
                avail_buttons = self.get_current_icons(available=True)
                current_icons = avail_buttons['icon'].tolist() if not avail_buttons.empty else []
                
                self.debug.log_event("DUNGEON_START", f"search_iteration_{i}", {
                    'icons_found': current_icons,
                    'looking_for': target_chapter,
                    'expanded_chapter': expanded > 0
                })
                
                # Look for correct chapter
                if (avail_buttons == target_chapter).any(axis=None):
                    pos = get_button_pos(avail_buttons, target_chapter)
                    chapter_found = True
                    
                    self.debug.log_event("DUNGEON_START", "chapter_found", {
                        'chapter': target_chapter,
                        'position': pos.tolist(),
                        'expanded': expanded > 0
                    })
                    
                    if not expanded:
                        expanded = 1
                        self.logger.info(f'Expanding chapter {target_chapter} at position {pos}')
                        self.click_button(pos + [500, 90])
                        time.sleep(2)  # Wait for chapter to expand
                        
                    # check button is near top of screen
                    if pos[1] < 550 and floor % 3 != 0:
                        # Stop scrolling when chapter is near top
                        self.logger.info(f'Chapter {target_chapter} positioned correctly')
                        break
                elif (avail_buttons == next_chapter).any(axis=None) and floor % 3 == 0:
                    pos = get_button_pos(avail_buttons, next_chapter)
                    chapter_found = True
                    self.logger.info(f'Found next chapter {next_chapter} for final floor')
                    # Stop scrolling if the next chapter is found and last floor of chapter is chosen
                    break
                
                # Continue swiping to find correct chapter
                [self.swipe([2, 0], [0, 0]) for i in range(2)]
                self.click(30, 600)  # stop scroll
                time.sleep(1)  # Give time for scroll to complete

            # Click play floor if found
            if not (pos == np.array([0, 0])).any() and chapter_found:
                floor_offset = None
                if floor % 3 == 0:
                    floor_offset = [30, -460]
                elif floor % 3 == 1:
                    floor_offset = [30, 485]
                elif floor % 3 == 2:
                    floor_offset = [30, 885]
                
                floor_button_pos = pos + floor_offset
                self.logger.info(f'Clicking floor {floor} button at position {floor_button_pos}')
                
                self.debug.log_event("DUNGEON_START", "clicking_floor", {
                    'floor': floor,
                    'chapter_pos': pos.tolist(),
                    'floor_offset': floor_offset,
                    'final_pos': floor_button_pos.tolist()
                })
                
                self.click_button(floor_button_pos)
                time.sleep(2)  # Wait for floor selection
                
                # Click start/continue button
                self.logger.info('Clicking start battle button')
                self.click_button((500, 600))
                
                # Wait for match to start with better validation
                match_started = False
                for i in range(15):  # Increased timeout
                    time.sleep(2)
                    avail_buttons = self.get_current_icons(available=True)
                    current_icons = avail_buttons['icon'].tolist() if not avail_buttons.empty else []
                    
                    self.debug.log_event("DUNGEON_START", f"waiting_for_match_{i}", {
                        'icons_detected': current_icons,
                        'waiting_for': ['fighting.png', 'back_button.png']
                    })
                    
                    self.logger.info(f'Waiting for match to start {i}/15 - Icons: {current_icons}')
                    
                    # Check if we're in battle
                    if avail_buttons['icon'].isin(['fighting.png']).any():
                        self.logger.info('✅ Successfully entered dungeon battle!')
                        match_started = True
                        break
                    # Check if we can go back (still in menu)
                    elif avail_buttons['icon'].isin(['back_button.png']).any():
                        self.logger.info('Still in dungeon menu, continuing to wait...')
                        continue
                    # Check if we're back at home screen (failed)
                    elif avail_buttons['icon'].isin(['home_screen.png', 'battle_icon.png']).any():
                        self.logger.warning('⚠️ Returned to home screen - dungeon selection may have failed')
                        break
                
                if not match_started:
                    self.debug.log_event("DUNGEON_START", "match_start_failed", {
                        'warning': 'Failed to detect battle start after floor selection'
                    }, warnings=["Dungeon may not have started properly"])
                    self.logger.warning('⚠️ Failed to confirm dungeon match started')
                    
            else:
                self.debug.log_event("DUNGEON_START", "chapter_not_found", {
                    'target_chapter': target_chapter,
                    'position_found': not (pos == np.array([0, 0])).any(),
                    'chapter_found': chapter_found
                }, warnings=["Could not locate target chapter for dungeon"])
                self.logger.warning(f'⚠️ Could not find chapter {target_chapter} for floor {floor}')
        else:
            self.debug.log_event("DUNGEON_START", "not_on_dungeon_page", {
                'current_icons': detected_icons
            }, warnings=["Not on dungeon page when play_dungeon was called"])
            self.logger.warning('⚠️ Not on dungeon page - cannot start dungeon')

    # Locate game home screen and try to start fight is chosen
    def battle_screen(self, start=False, pve=True, floor=5):
        start_time = time.time()
        
        # Debug screen state analysis
        self.debug.debug_action_plan(self, 'battle_screen_analysis', {
            'start_mode': start,
            'pve_mode': pve,
            'target_floor': floor
        }, expected_outcome="Screen state identified")
        
        # Scan screen for any key buttons
        df = self.get_current_icons(available=True)
        
        # Debug icon detection results
        detected_icons = df['icon'].tolist() if not df.empty else []
        self.debug.log_event("SCREEN_ANALYSIS", "icon_detection", {
            'icons_detected': detected_icons,
            'total_icons': len(detected_icons),
            'screen_empty': df.empty
        })
        
        screen_state = None
        action_taken = None
        
        if not df.empty:
            # list of buttons
            if (df == 'fighting.png').any(axis=None) and not (df == '0cont_button.png').any(axis=None):
                screen_state = 'fighting'
                self.debug.log_event("SCREEN_STATE", "combat_detected", {
                    'state': 'fighting',
                    'combat_active': True
                })
                return df, 'fighting'
                
            if (df == 'friend_menu.png').any(axis=None):
                screen_state = 'friend_menu'
                action_taken = 'close_friend_menu'
                self.debug.log_event("SCREEN_STATE", "friend_menu_detected", {
                    'action': 'clicking to close'
                })
                self.click_button(np.array([100, 600]))
                return df, 'friend_menu'
                
            # Start pvp if homescreen
            if (df == 'home_screen.png').any(axis=None) and (df == 'battle_icon.png').any(axis=None):
                screen_state = 'home_screen'
                if pve and start:
                    action_taken = 'start_pve_dungeon'
                    self.debug.log_event("SCREEN_STATE", "starting_pve", {
                        'floor': floor,
                        'mode': 'PvE dungeon'
                    })
                    self.logger.info(f'🎯 Starting PvE dungeon floor {floor}')
                    # Add a 500 pixel offset for PvE button
                    self.click_button(np.array([640, 1259]))
                    time.sleep(3)  # Wait for PvE menu to load
                    
                    # Verify we're on dungeon page before calling play_dungeon
                    avail_buttons = self.get_current_icons(available=True)
                    if (avail_buttons == 'dungeon_page.png').any(axis=None):
                        self.logger.info('✅ Successfully navigated to dungeon page')
                        self.play_dungeon(floor=floor)
                    else:
                        self.logger.warning('⚠️ Failed to navigate to dungeon page, retrying...')
                        self.debug.log_event("SCREEN_STATE", "pve_navigation_failed", {
                            'current_icons': avail_buttons['icon'].tolist() if not avail_buttons.empty else [],
                            'expected': 'dungeon_page.png'
                        }, warnings=["Failed to reach dungeon page after clicking PvE button"])
                        # Try clicking PvE button again
                        time.sleep(2)
                        self.click_button(np.array([640, 1259]))
                        time.sleep(3)
                elif start:
                    action_taken = 'start_pvp'
                    self.debug.log_event("SCREEN_STATE", "starting_pvp", {
                        'mode': 'PvP battle'
                    })
                    self.logger.info('🎯 Starting PvP battle')
                    self.click_button(np.array([140, 1259]))
                time.sleep(1)
                return df, 'home'
                
            # Check first button is clickable
            df_click = df[df['icon'].isin(['back_button.png', 'battle_icon.png', '0cont_button.png', '1quit.png'])]
            if not df_click.empty:
                screen_state = 'menu_interface'
                action_taken = 'click_menu_button'
                button_clicked = df_click.iloc[0]['icon']
                button_pos = df_click['pos [X,Y]'].tolist()[0]
                
                self.debug.log_event("SCREEN_STATE", "menu_button_clicked", {
                    'button': button_clicked,
                    'position': button_pos
                })
                
                self.click_button(button_pos)
                return df, 'menu'
        else:
            screen_state = 'unknown_empty'
            self.debug.log_event("SCREEN_STATE", "no_icons_detected", {
                'warning': 'No recognizable UI elements found'
            }, warnings=["Screen appears blank or unrecognized"])
        
        # Fallback action
        action_taken = 'force_back_keypress'
        self.debug.log_event("SCREEN_STATE", "fallback_action", {
            'action': 'sending back key',
            'reason': 'No other options available'
        }, warnings=["Using fallback back key - screen state unclear"])
        
        self.shell(f'input keyevent {const.KEYCODE_BACK}')  #Force back
        
        # Summary debug log
        duration = time.time() - start_time
        self.debug.log_event("BATTLE_SCREEN", "analysis_complete", {
            'screen_state': screen_state,
            'action_taken': action_taken,
            'duration': duration,
            'icons_found': detected_icons
        })
        
        return df, 'lost'

    # Navigate and locate store refresh button from battle screen
    def find_store_refresh(self):
        self.click_button((100, 1500))  # Click store button
        [self.swipe([0, 0], [2, 0]) for i in range(5)]  # swipe to top
        self.click(30, 150)  # stop scroll
        avail_buttons = self.get_current_icons(available=True)
        if (avail_buttons == 'refresh_button.png').any(axis=None):
            pos = get_button_pos(avail_buttons, 'refresh_button.png')
            return pos

    # Refresh items in shop when available
    def refresh_shop(self):
        self.click_button((100, 1500))  # Click store button
        self.click_button((475, 1300))  # Click store button
        # Scroll up and find the refresh button
        pos = self.find_store_refresh()
        if isinstance(pos, np.ndarray):
            self.click_button(pos - [300, 820])  # Click first (free) item
            self.click(400, 1165)  # buy
            self.click(30, 150)  # remove pop-up
            self.click_button(pos + [400, -400])  # Click last item (possible legendary)
            self.click(400, 1165)  # buy
            self.click(30, 150)  # remove pop-up
            self.logger.warning('Bought store units!')
            # Try to refresh shop (watch ad)
            self.click_button(pos)

    def watch_ads(self):
        avail_buttons = self.get_current_icons(available=True)
        # Watch ad if available
        if (avail_buttons == 'quest_done.png').any(axis=None):
            pos = get_button_pos(avail_buttons, 'quest_done.png')
            self.click_button(pos)
            self.click(700, 600)  # collect second completed quest
            self.click(700, 400)  # collect second completed quest
            [self.click(150, 250) for i in range(2)]  # click dailies twice
            self.click(420, 420)  # collect ad chest
        elif (avail_buttons == 'ad_season.png').any(axis=None):
            pos = get_button_pos(avail_buttons, 'ad_season.png')
            self.click_button(pos)
        elif (avail_buttons == 'ad_pve.png').any(axis=None):
            pos = get_button_pos(avail_buttons, 'ad_pve.png')
            self.click_button(pos)
        elif (avail_buttons == 'battle_icon.png').any(axis=None):
            self.refresh_shop()
        else:
            #self.logger.info('Watched all ads!')
            return
        # Check if ad was started
        avail_buttons, status = self.battle_screen()
        if status == 'menu' or status == 'home' or (avail_buttons == 'refresh_button.png').any(axis=None):
            self.logger.info('FINISHED AD')
        # Watch ad
        else:
            time.sleep(30)
            # Keep watching until back in menu
            for i in range(10):
                avail_buttons, status = self.battle_screen()
                if status == 'menu' or status == 'home':
                    self.logger.info('FINISHED AD')
                    return  # Exit function
                time.sleep(2)
                self.click(870, 30)  # skip forward/click X
                self.click(870, 100)  # click X playstore popup
                if i > 5:
                    self.shell(f'input keyevent {const.KEYCODE_BACK}')  #Force back
                self.logger.info(f'AD TIME {i} {status}')
            # Restart game if can't escape ad
            self.restart_RR()


####
#### END OF CLASS
####


# Get fight grid pixel values
def get_grid():
    #Grid dimensions
    top_box = (153, 945)
    box_size = (120, 120)
    gap = 0
    height = 3
    width = 5
    # x_cords
    x_cord = list(range(top_box[0], top_box[0] + (box_size[0] + gap) * width, box_size[0] + gap))
    y_cord = list(range(top_box[1], top_box[1] + (box_size[1] + gap) * height, box_size[1] + gap))
    boxes = []
    # Create list of all boxes
    for y_point in y_cord:
        for x_point in x_cord:
            boxes.append((x_point, y_point))
    # Convert to np array (4x4) with x,y coords
    boxes = np.array(boxes).reshape(height, width, 2)
    return boxes, box_size


def get_unit_count(grid_df):
    df_split = grid_df.groupby("unit")
    df_groups = df_split["unit"].count()
    if not 'empty.png' in df_groups:
        df_groups['empty.png'] = 0
    unit_list = list(df_groups.index)
    return df_split, df_groups, unit_list


# Removes 1x of the highest rank unit from the merge_series
def preserve_unit(unit_series, target='chemist.png', keep_min=False):
    """
    Remove 1x of the highest rank unit from the merge_series
    param: merge_series - pandas series of units to remove
    param: target - target unit to keep
    param: keep_min - if true, keep the lowest rank unit instead of highest
    """
    merge_series = unit_series.copy()
    preserve_series = adv_filter_keys(merge_series, units=target, remove=False)
    if not preserve_series.empty:
        if keep_min:
            preserve_unit = preserve_series.index.min()
        else:
            preserve_unit = preserve_series.index.max()
        # Remove 1 count of highest/lowest rank
        merge_series[merge_series.index == preserve_unit] = merge_series[merge_series.index == preserve_unit] - 1
        # Remove 0 counts
        return merge_series[merge_series > 0]
    else:
        return merge_series


def grid_meta_info(grid_df, min_age=0):
    """
    Split grid df into unique units and ranks
    Shows total count of unit and count of each rank
    param: grid_df - pandas dataframe of grid
    param: min_age - minimum age of unit to include in meta info
    """
    # Split by unique unit
    df_groups = get_unit_count(grid_df)[1]
    grid_df = grid_df[grid_df['Age'] >= min_age].reset_index(drop=True)
    df_split = grid_df.groupby(['unit', 'rank'])
    # Count number of unit of each rank
    unit_series = df_split['unit'].count()
    #unit_series = unit_series.sort_values(ascending=False)
    group_keys = list(unit_series.index)
    return df_split, unit_series, df_groups, group_keys


def filter_units(unit_series, units):
    if not isinstance(units, list):  # Make units a list if not already
        units = [units]
    # Create temp series to hold matches
    series = []
    merge_series = unit_series.copy()
    for token in units:
        if isinstance(token, int):
            exists = merge_series.index.get_level_values('rank').isin([token]).any()
            if exists:
                series.append(merge_series.xs(token, level='rank', drop_level=False))
            else:
                continue  # skip if nothing matches criteria
        elif isinstance(token, str):
            if token in merge_series:
                series.append(merge_series.xs(token, level='unit', drop_level=False))
            else:
                continue
    if not len(series) == 0:
        temp_series = pd.concat(series)
        # Select all entries from original series that are in temp_series
        merge_series = merge_series[merge_series.index.isin(temp_series.index)]
        return merge_series
    else:
        return pd.Series(dtype=object)


def adv_filter_keys(unit_series, units=None, ranks=None, remove=False):
    """
    Returns all elements which match units and ranks values
    If one of the parameters is None, it is ignored and all values are kept
    If remove is True, all elements are removed which do not match the criteria
    param: unit_series - pandas series of units to filter
    param: units - string or list of strings of units to filter by
    param: ranks - int or list of ints of ranks to filter by
    param: remove - if true, return filtered series, if false, return only matches
    """
    # return if no units in series
    if unit_series.empty:
        return pd.Series(dtype=object)
    filtered_ranks = pd.Series(dtype=object)
    if not units is None:
        filtered_units = filter_units(unit_series, units)
    else:
        filtered_units = unit_series.copy()
    # if all units are filtered already, return empty series
    if not ranks is None and not filtered_units.empty:
        filtered_ranks = filter_units(filtered_units, ranks)
    else:
        filtered_ranks = filtered_units.copy()
    # Final filtering
    series = unit_series.copy()
    if remove:
        series = series[~series.index.isin(filtered_ranks.index)]
    else:
        series = series[series.index.isin(filtered_ranks.index)]
    return series


# Will spam read all knowledge in knowledge base for free gold, roughly 3k, 100 gems
def read_knowledge(bot):
    spam_click = range(1000)
    for i in spam_click:
        bot.click(450, 1300, 0.1)


def get_button_pos(df, button):
    #button=button+'.png'
    pos = df[df['icon'] == button]['pos [X,Y]'].reset_index(drop=True)[0]
    return np.array(pos)
