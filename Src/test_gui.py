import configparser
import tkinter as tk
import pytest
from gui import create_options, create_combat_info, write_to_widget

def _make_root():
    try:
        return tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter display not available")


def test_create_options_sets_expected_defaults():
    root = _make_root()
    frame = tk.Frame(root)
    cfg = configparser.ConfigParser()
    cfg["bot"] = {"pve": "1", "mana_level": "1,3,5", "floor": "7"}
    ads_var, pve_var, mana_vars, floor = create_options(frame, cfg)

    assert ads_var.get() == 0
    assert pve_var.get() == 1
    assert [v.get() for v in mana_vars] == [1, 0, 1, 0, 1]
    assert floor.get() == "7"
    root.destroy()


def test_create_combat_info_returns_text_widgets():
    root = _make_root()
    frame = tk.Frame(root)
    grid_dump, unit_dump, merge_dump = create_combat_info(frame)

    assert isinstance(grid_dump, tk.Text)
    assert isinstance(unit_dump, tk.Text)
    assert isinstance(merge_dump, tk.Text)
    root.destroy()


def test_write_to_widget_inserts_and_locks_text():
    root = _make_root()
    tbox = tk.Text(root)
    tbox.pack()

    write_to_widget(root, tbox, "hello world")

    assert tbox.cget("state") == tk.DISABLED
    tbox.config(state=tk.NORMAL)
    assert tbox.get("1.0", tk.END).strip() == "hello world"
    root.destroy()