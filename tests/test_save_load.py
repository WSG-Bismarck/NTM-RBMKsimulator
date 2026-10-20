"""阶段 3 保存/导出测试：JSON 往返一致、非法文件报错、文件读写。"""
import json

import pytest

from rbmk.model.reactor import ReactorModel
from rbmk.model import save_load
from rbmk.model.components import ComponentType, ControlGroup


def _sample_model() -> ReactorModel:
    m = ReactorModel(rows=8, cols=8)
    m.global_insertion = 60.0
    m.group_insertion["RED"] = 30.0
    m.coolant_flow = 70.0
    m.place(2, 3, ComponentType.RBMK_ROD, fuel="rbmk_fuel_heu235")
    m.place(2, 4, ComponentType.RBMK_CONTROL, group=ControlGroup.RED, insertion=45.0)
    m.place(3, 3, ComponentType.RBMK_MODERATOR)
    m.place(4, 4, ComponentType.RBMK_BOILER)
    return m


def test_json_roundtrip_preserves_layout_and_params():
    m = _sample_model()
    text = save_load.to_json(m)
    m2 = save_load.from_json(text)

    assert (m2.rows, m2.cols) == (8, 8)
    assert m2.global_insertion == 60.0
    assert m2.group_insertion["RED"] == 30.0
    assert m2.coolant_flow == 70.0
    assert m2.counts() == m.counts()
    c = m2.cell_at(2, 4)
    assert c.comp == ComponentType.RBMK_CONTROL
    assert c.group == ControlGroup.RED
    assert c.insertion == 45.0
    f = m2.cell_at(2, 3)
    assert f.fuel == "rbmk_fuel_heu235"


def test_save_and_load_file(tmp_path):
    m = _sample_model()
    p = tmp_path / "design.rbmk.json"
    save_load.save(m, p)
    assert p.exists()
    m2 = save_load.load(p)
    assert m2.to_dict() == m.to_dict()


def test_invalid_json_missing_rows():
    with pytest.raises(ValueError):
        save_load.from_json(json.dumps({"cols": 5}))


def test_invalid_cell_out_of_bounds():
    bad = {"rows": 3, "cols": 3, "cells": [{"r": 9, "c": 0, "comp": "FUEL"}]}
    with pytest.raises(ValueError):
        save_load.from_json(json.dumps(bad))


def test_export_is_importable():
    """导出分享文件能被导入，且布局一致。"""
    m = _sample_model()
    text = save_load.to_json(m)
    m2 = save_load.from_json(text)
    assert m2.to_dict() == m.to_dict()
