"""
Tests for ArcaneWeaver Entity System Components.

This module contains comprehensive tests for:
- ComponentModel (base class)
- StatComponent
- InventoryCellComponent
"""

import pytest
from pydantic import ValidationError

from arcaneweaver.core.entity_system.components import (
    ComponentModel,
    StatComponent,
    StatsComponent,
    InventoryCellComponent,
    InventoryComponent,
    ComponentType,
    FieldType,
)


class TestFieldType:
    """Tests for FieldType enum."""

    def test_field_type_values(self):
        """Test that FieldType enum has expected values."""
        assert FieldType.NUMBER.value == "number"
        assert FieldType.TEXT.value == "text"
        assert FieldType.CHECKBOX.value == "checkbox"
        assert FieldType.LIST.value == "list"
        assert FieldType.OBJECT.value == "object"
        assert FieldType.SELECT.value == "select"
        assert FieldType.TEXTAREA.value == "textarea"


class TestComponentType:
    """Tests for ComponentType enum."""

    def test_component_type_values(self):
        """Test that ComponentType enum has expected values."""
        assert ComponentType.STAT.value == "stat"
        assert ComponentType.INVENTORY.value == "inventory"
        assert ComponentType.CUSTOM.value == "custom"


class TestComponentModel:
    """Tests for ComponentModel base class."""

    def test_component_model_default(self):
        """Test ComponentModel with default values."""
        component = ComponentModel()
        assert component.component_type == ComponentType.CUSTOM

    def test_component_model_custom_type(self):
        """Test ComponentModel with custom component type."""
        component = ComponentModel(component_type=ComponentType.STAT)
        assert component.component_type == ComponentType.STAT

    def test_component_model_extra_fields(self):
        """Test ComponentModel accepts extra fields."""
        component = ComponentModel(custom_field="test", another_field=42)
        assert component.custom_field == "test"
        assert component.another_field == 42

    def test_get_editor_config_basic(self):
        """Test get_editor_config for basic component."""
        component = ComponentModel()
        config = component.get_editor_config()
        
        # Should not include component_type in editor config
        assert "component_type" not in config

    def test_get_editor_config_with_extra(self):
        """Test get_editor_config includes extra fields."""
        component = ComponentModel(dynamic_field="test", number_field=123)
        config = component.get_editor_config()
        
        assert "dynamic_field" in config
        assert "number_field" in config
        assert config["dynamic_field"]["type"] == FieldType.TEXT
        assert config["number_field"]["type"] == FieldType.NUMBER

    def test_infer_value_type(self):
        """Test _infer_value_type for different value types."""
        component = ComponentModel()
        
        assert component._infer_value_type(42) == FieldType.NUMBER
        assert component._infer_value_type(3.14) == FieldType.NUMBER
        assert component._infer_value_type("text") == FieldType.TEXT
        assert component._infer_value_type(True) == FieldType.CHECKBOX
        assert component._infer_value_type([1, 2, 3]) == FieldType.LIST
        assert component._infer_value_type({"key": "value"}) == FieldType.OBJECT
        assert component._infer_value_type(None) == FieldType.TEXT  # Default for unknown


class TestStatComponent:
    """Tests for StatComponent."""

    def test_stat_component_basic_creation(self):
        """Test basic StatComponent creation."""
        stat = StatComponent(name="strength", base_value=10.0)
        assert stat.name == "strength"
        assert stat.base_value == 10.0
        assert stat.current_value == 10.0  # Should default to base_value
        assert stat.component_type == ComponentType.STAT

    def test_stat_component_with_current_value(self):
        """Test StatComponent with explicit current_value."""
        stat = StatComponent(name="health", base_value=100.0, current_value=75.0)
        assert stat.base_value == 100.0
        assert stat.current_value == 75.0

    def test_stat_component_with_constraints(self):
        """Test StatComponent with min/max constraints."""
        stat = StatComponent(
            name="mana",
            base_value=50.0,
            min_value=0.0,
            max_value=100.0
        )
        assert stat.min_value == 0.0
        assert stat.max_value == 100.0

    def test_stat_component_name_required(self):
        """Test that name is required for StatComponent."""
        with pytest.raises(ValidationError):
            StatComponent(base_value=10.0)

    def test_stat_component_validation_min_value(self):
        """Test that current_value respects min_value constraint."""
        stat = StatComponent(
            name="health",
            base_value=10.0,
            min_value=0.0,
            max_value=100.0
        )
        # Try to set below minimum
        stat.current_value = -5.0
        assert stat.current_value == 0.0  # Should be clamped to min_value

    def test_stat_component_validation_max_value(self):
        """Test that current_value respects max_value constraint."""
        stat = StatComponent(
            name="mana",
            base_value=50.0,
            min_value=0.0,
            max_value=100.0
        )
        # Try to set above maximum
        stat.current_value = 150.0
        assert stat.current_value == 100.0  # Should be clamped to max_value

    def test_stat_component_validation_base_value_min(self):
        """Test that base_value respects min_value constraint."""
        stat = StatComponent(
            name="health",
            base_value=10.0,
            min_value=0.0,
            max_value=100.0
        )
        stat.base_value = -10.0
        assert stat.base_value == 0.0  # Should be clamped to min_value

    def test_stat_component_validation_base_value_max(self):
        """Test that base_value respects max_value constraint."""
        stat = StatComponent(
            name="mana",
            base_value=50.0,
            min_value=0.0,
            max_value=100.0
        )
        stat.base_value = 150.0
        assert stat.base_value == 100.0  # Should be clamped to max_value

    def test_modify_value_increase(self):
        """Test modify_value increases current value."""
        stat = StatComponent(name="strength", base_value=10.0)
        result = stat.modify_value(5.0)
        assert result == 15.0
        assert stat.current_value == 15.0
        assert stat.base_value == 10.0  # Base should not change

    def test_modify_value_decrease(self):
        """Test modify_value decreases current value."""
        stat = StatComponent(name="health", base_value=100.0, current_value=75.0)
        result = stat.modify_value(-20.0)
        assert result == 55.0
        assert stat.current_value == 55.0

    def test_modify_value_respects_min(self):
        """Test modify_value respects min_value constraint."""
        stat = StatComponent(
            name="mana",
            base_value=50.0,
            current_value=10.0,
            min_value=0.0,
            max_value=100.0
        )
        result = stat.modify_value(-50.0)  # Would go below 0
        assert result == 0.0
        assert stat.current_value == 0.0

    def test_modify_value_respects_max(self):
        """Test modify_value respects max_value constraint."""
        stat = StatComponent(
            name="health",
            base_value=80.0,
            current_value=90.0,
            min_value=0.0,
            max_value=100.0
        )
        result = stat.modify_value(50.0)  # Would go above 100
        assert result == 100.0
        assert stat.current_value == 100.0

    def test_reset_to_base(self):
        """Test reset_to_base resets current_value to base_value."""
        stat = StatComponent(name="strength", base_value=10.0, current_value=15.0)
        stat.reset_to_base()
        assert stat.current_value == 10.0
        assert stat.base_value == 10.0

    def test_set_base_value(self):
        """Test set_base_value sets both base and current values."""
        stat = StatComponent(name="mana", base_value=50.0, current_value=40.0)
        result = stat.set_base_value(60.0)
        assert result == 60.0
        assert stat.base_value == 60.0
        assert stat.current_value == 60.0

    def test_set_base_value_respects_min(self):
        """Test set_base_value respects min_value constraint."""
        stat = StatComponent(
            name="health",
            base_value=50.0,
            min_value=0.0,
            max_value=100.0
        )
        result = stat.set_base_value(-10.0)
        assert result == 0.0
        assert stat.base_value == 0.0
        assert stat.current_value == 0.0

    def test_set_base_value_respects_max(self):
        """Test set_base_value respects max_value constraint."""
        stat = StatComponent(
            name="mana",
            base_value=50.0,
            min_value=0.0,
            max_value=100.0
        )
        result = stat.set_base_value(150.0)
        assert result == 100.0
        assert stat.base_value == 100.0
        assert stat.current_value == 100.0

    def test_stat_component_with_description(self):
        """Test StatComponent with description."""
        stat = StatComponent(
            name="intelligence",
            base_value=12.0,
            description="Mental acuity and reasoning"
        )
        assert stat.description == "Mental acuity and reasoning"

    def test_stat_component_extra_fields(self):
        """Test StatComponent accepts extra fields."""
        stat = StatComponent(
            name="strength",
            base_value=10.0,
            custom_metadata="test"
        )
        assert stat.custom_metadata == "test"


class TestStatsComponent:
    """Tests for StatsComponent (collection of statistics)."""

    def test_stats_component_basic_creation(self):
        """Test basic StatsComponent creation."""
        stats = StatsComponent()
        assert stats.component_type == ComponentType.STAT
        assert stats.stats == []
        assert stats.max_stats is None

    def test_stats_component_with_max_stats(self):
        """Test StatsComponent with max_stats limit."""
        stats = StatsComponent(max_stats=5)
        assert stats.max_stats == 5

    def test_add_stat_basic(self):
        """Test adding a statistic."""
        stats = StatsComponent()
        stat = stats.add_stat("strength", base_value=15.0)
        assert stat.name == "strength"
        assert stat.base_value == 15.0
        assert stat.current_value == 15.0
        assert len(stats.stats) == 1

    def test_add_stat_with_all_parameters(self):
        """Test adding stat with all parameters."""
        stats = StatsComponent()
        stat = stats.add_stat(
            name="health",
            base_value=100.0,
            current_value=75.0,
            min_value=0.0,
            max_value=100.0,
            description="Current health"
        )
        assert stat.name == "health"
        assert stat.base_value == 100.0
        assert stat.current_value == 75.0
        assert stat.min_value == 0.0
        assert stat.max_value == 100.0
        assert stat.description == "Current health"

    def test_add_stat_duplicate_name_raises_error(self):
        """Test adding stat with duplicate name raises error."""
        stats = StatsComponent()
        stats.add_stat("strength", 15.0)
        with pytest.raises(ValueError, match="already exists"):
            stats.add_stat("strength", 10.0)

    def test_add_stat_replace_if_exists(self):
        """Test adding stat with replace_if_exists=True."""
        stats = StatsComponent()
        stats.add_stat("strength", 15.0)
        new_stat = stats.add_stat("strength", 20.0, replace_if_exists=True)
        assert len(stats.stats) == 1
        assert new_stat.base_value == 20.0

    def test_add_stat_respects_max_stats(self):
        """Test adding stat respects max_stats limit."""
        stats = StatsComponent(max_stats=2)
        stats.add_stat("stat1", 10.0)
        stats.add_stat("stat2", 10.0)
        with pytest.raises(ValueError, match="maximum number of stats"):
            stats.add_stat("stat3", 10.0)

    def test_remove_stat_success(self):
        """Test removing a statistic successfully."""
        stats = StatsComponent()
        stats.add_stat("strength", 15.0)
        result = stats.remove_stat("strength")
        assert result is True
        assert len(stats.stats) == 0

    def test_remove_stat_not_found(self):
        """Test removing non-existent statistic."""
        stats = StatsComponent()
        result = stats.remove_stat("nonexistent")
        assert result is False

    def test_get_stat_success(self):
        """Test getting a statistic."""
        stats = StatsComponent()
        stats.add_stat("strength", 15.0)
        stat = stats.get_stat("strength")
        assert stat is not None
        assert stat.name == "strength"
        assert stat.base_value == 15.0

    def test_get_stat_not_found(self):
        """Test getting non-existent statistic."""
        stats = StatsComponent()
        stat = stats.get_stat("nonexistent")
        assert stat is None

    def test_has_stat_true(self):
        """Test has_stat returns True when stat exists."""
        stats = StatsComponent()
        stats.add_stat("strength", 15.0)
        assert stats.has_stat("strength") is True

    def test_has_stat_false(self):
        """Test has_stat returns False when stat doesn't exist."""
        stats = StatsComponent()
        assert stats.has_stat("strength") is False

    def test_modify_stat_success(self):
        """Test modifying a statistic."""
        stats = StatsComponent()
        stats.add_stat("health", base_value=100.0, current_value=75.0)
        new_value = stats.modify_stat("health", 10.0)
        assert new_value == 85.0
        assert stats.get_stat("health").current_value == 85.0

    def test_modify_stat_not_found(self):
        """Test modifying non-existent statistic."""
        stats = StatsComponent()
        result = stats.modify_stat("nonexistent", 10.0)
        assert result is None

    def test_modify_stat_respects_constraints(self):
        """Test modify_stat respects min/max constraints."""
        stats = StatsComponent()
        stats.add_stat("health", base_value=50.0, min_value=0.0, max_value=100.0)
        # Try to modify beyond max
        new_value = stats.modify_stat("health", 100.0)
        assert new_value == 100.0  # Should be clamped

    def test_set_stat_base_value(self):
        """Test setting base value of a statistic."""
        stats = StatsComponent()
        stats.add_stat("strength", base_value=10.0)
        new_base = stats.set_stat_base_value("strength", 15.0)
        assert new_base == 15.0
        assert stats.get_stat("strength").base_value == 15.0
        assert stats.get_stat("strength").current_value == 15.0

    def test_set_stat_base_value_not_found(self):
        """Test setting base value of non-existent stat."""
        stats = StatsComponent()
        result = stats.set_stat_base_value("nonexistent", 10.0)
        assert result is None

    def test_set_stat_current_value(self):
        """Test setting current value of a statistic."""
        stats = StatsComponent()
        stats.add_stat("health", base_value=100.0, current_value=75.0)
        new_current = stats.set_stat_current_value("health", 50.0)
        assert new_current == 50.0
        assert stats.get_stat("health").current_value == 50.0
        assert stats.get_stat("health").base_value == 100.0  # Base unchanged

    def test_set_stat_current_value_not_found(self):
        """Test setting current value of non-existent stat."""
        stats = StatsComponent()
        result = stats.set_stat_current_value("nonexistent", 10.0)
        assert result is None

    def test_reset_stat_to_base(self):
        """Test resetting a statistic to base value."""
        stats = StatsComponent()
        stats.add_stat("health", base_value=100.0, current_value=50.0)
        result = stats.reset_stat_to_base("health")
        assert result is True
        assert stats.get_stat("health").current_value == 100.0

    def test_reset_stat_to_base_not_found(self):
        """Test resetting non-existent statistic."""
        stats = StatsComponent()
        result = stats.reset_stat_to_base("nonexistent")
        assert result is False

    def test_reset_all_to_base(self):
        """Test resetting all statistics to base values."""
        stats = StatsComponent()
        stats.add_stat("health", base_value=100.0, current_value=50.0)
        stats.add_stat("mana", base_value=50.0, current_value=25.0)
        stats.reset_all_to_base()
        assert stats.get_stat("health").current_value == 100.0
        assert stats.get_stat("mana").current_value == 50.0

    def test_get_stat_names(self):
        """Test getting list of all statistic names."""
        stats = StatsComponent()
        stats.add_stat("strength", 15.0)
        stats.add_stat("health", 100.0)
        names = stats.get_stat_names()
        assert "strength" in names
        assert "health" in names
        assert len(names) == 2

    def test_get_stat_names_empty(self):
        """Test getting stat names from empty collection."""
        stats = StatsComponent()
        names = stats.get_stat_names()
        assert names == []

    def test_get_all_stats(self):
        """Test getting all statistics."""
        stats = StatsComponent()
        stats.add_stat("strength", 15.0)
        stats.add_stat("health", 100.0)
        all_stats = stats.get_all_stats()
        assert len(all_stats) == 2
        assert all(isinstance(stat, StatComponent) for stat in all_stats)

    def test_clear_all_stats(self):
        """Test clearing all statistics."""
        stats = StatsComponent()
        stats.add_stat("strength", 15.0)
        stats.add_stat("health", 100.0)
        count = stats.clear_all_stats()
        assert count == 2
        assert len(stats.stats) == 0

    def test_clear_all_stats_empty(self):
        """Test clearing stats from empty collection."""
        stats = StatsComponent()
        count = stats.clear_all_stats()
        assert count == 0

    def test_stats_component_multiple_operations(self):
        """Test multiple operations on stats component."""
        stats = StatsComponent()
        
        # Add multiple stats
        stats.add_stat("strength", 15.0)
        stats.add_stat("health", base_value=100.0, current_value=75.0)
        stats.add_stat("mana", base_value=50.0, min_value=0.0, max_value=100.0)
        
        # Modify stats
        stats.modify_stat("health", 10.0)
        stats.modify_stat("mana", -5.0)
        
        # Verify
        assert stats.get_stat("health").current_value == 85.0
        assert stats.get_stat("mana").current_value == 45.0
        
        # Remove a stat
        stats.remove_stat("strength")
        assert len(stats.stats) == 2
        assert stats.has_stat("strength") is False

    def test_stats_component_serialization(self):
        """Test StatsComponent can be serialized."""
        stats = StatsComponent()
        stats.add_stat("strength", 15.0)
        data = stats.model_dump()
        assert "stats" in data
        assert "max_stats" in data
        assert len(data["stats"]) == 1


class TestInventoryCellComponent:
    """Tests for InventoryCellComponent."""

    def test_inventory_cell_component_basic_creation(self):
        """Test basic InventoryCellComponent creation."""
        inv = InventoryCellComponent()
        assert inv.component_type == ComponentType.INVENTORY
        assert inv.item_id is None
        assert inv.quantity == 0
        assert inv.max_stack_size == 1
        assert inv.slot_type is None
        assert inv.is_equipped is False

    def test_inventory_component_with_max_stack(self):
        """Test InventoryCellComponent with custom max_stack_size."""
        inv = InventoryCellComponent(max_stack_size=10)
        assert inv.max_stack_size == 10

    def test_inventory_component_with_slot_type(self):
        """Test InventoryCellComponent with slot_type."""
        inv = InventoryCellComponent(slot_type="weapon")
        assert inv.slot_type == "weapon"

    def test_inventory_component_validation_quantity_exceeds_max(self):
        """Test that quantity cannot exceed max_stack_size."""
        # Use add_items to set quantity, then try to exceed max
        inv = InventoryCellComponent(max_stack_size=5)
        inv.add_items("item", 5)
        assert inv.quantity == 5
        # Now try to set quantity above max (should be clamped)
        original_quantity = inv.quantity
        inv.quantity = 10
        assert inv.quantity == 5  # Should be clamped to max_stack_size

    def test_inventory_component_validation_quantity_negative(self):
        """Test that quantity cannot be negative."""
        inv = InventoryCellComponent()
        with pytest.raises(ValidationError):
            inv.quantity = -5

    def test_inventory_component_validation_quantity_without_item_id(self):
        """Test that quantity > 0 requires item_id."""
        with pytest.raises(ValueError, match="Cannot have quantity > 0 without an item_id"):
            InventoryCellComponent(quantity=5, item_id=None)

    def test_inventory_component_validation_clears_item_id_when_quantity_zero(self):
        """Test that item_id is cleared when quantity becomes 0."""
        inv = InventoryCellComponent(item_id="sword", quantity=1)
        inv.quantity = 0
        # The validator should clear item_id
        assert inv.item_id is None

    def test_is_empty_true_when_no_items(self):
        """Test is_empty returns True for empty slot."""
        inv = InventoryCellComponent()
        assert inv.is_empty() is True

    def test_is_empty_true_when_item_id_none(self):
        """Test is_empty returns True when item_id is None."""
        inv = InventoryCellComponent(quantity=0, item_id=None)
        assert inv.is_empty() is True

    def test_is_empty_false_when_has_items(self):
        """Test is_empty returns False when slot has items."""
        inv = InventoryCellComponent(item_id="sword", quantity=1)
        assert inv.is_empty() is False

    def test_is_full_true_when_at_max(self):
        """Test is_full returns True when at max capacity."""
        # Use add_items to properly set quantity to max
        inv = InventoryCellComponent(max_stack_size=5)
        inv.add_items("potion", 5)
        assert inv.is_full() is True
        assert inv.quantity == 5

    def test_is_full_false_when_below_max(self):
        """Test is_full returns False when below max capacity."""
        inv = InventoryCellComponent(max_stack_size=5)
        inv.add_items("potion", 3)
        assert inv.is_full() is False

    def test_add_items_to_empty_slot(self):
        """Test adding items to empty slot."""
        inv = InventoryCellComponent()
        added = inv.add_items("sword", 1)
        assert added == 1
        assert inv.item_id == "sword"
        assert inv.quantity == 1

    def test_add_items_partial_add(self):
        """Test adding more items than space allows."""
        inv = InventoryCellComponent(max_stack_size=5)
        inv.add_items("potion", 3)
        assert inv.quantity == 3
        added = inv.add_items("potion", 5)  # Only 2 can fit
        assert added == 2
        assert inv.quantity == 5
        assert inv.is_full() is True

    def test_add_items_different_item_id(self):
        """Test adding different item to occupied slot."""
        inv = InventoryCellComponent(max_stack_size=10)
        inv.add_items("sword", 1)
        added = inv.add_items("axe", 1)
        assert added == 0  # Cannot add different items
        assert inv.item_id == "sword"
        assert inv.quantity == 1

    def test_add_items_zero_or_negative(self):
        """Test adding zero or negative items."""
        inv = InventoryCellComponent(max_stack_size=10)
        inv.add_items("sword", 1)
        assert inv.add_items("sword", 0) == 0
        assert inv.add_items("sword", -5) == 0
        assert inv.quantity == 1  # Should not change

    def test_remove_items_partial(self):
        """Test removing some items."""
        inv = InventoryCellComponent(max_stack_size=10)
        inv.add_items("potion", 5)
        removed = inv.remove_items(2)
        assert removed == 2
        assert inv.quantity == 3
        assert inv.item_id == "potion"

    def test_remove_items_all(self):
        """Test removing all items."""
        inv = InventoryCellComponent(max_stack_size=10)
        inv.add_items("sword", 3)
        removed = inv.remove_items(3)
        assert removed == 3
        assert inv.quantity == 0
        assert inv.item_id is None  # Should be cleared

    def test_remove_items_more_than_available(self):
        """Test removing more items than available."""
        inv = InventoryCellComponent(max_stack_size=10)
        inv.add_items("potion", 2)
        removed = inv.remove_items(5)
        assert removed == 2
        assert inv.quantity == 0
        assert inv.item_id is None

    def test_remove_items_zero_or_negative(self):
        """Test removing zero or negative items."""
        inv = InventoryCellComponent(max_stack_size=10)
        inv.add_items("sword", 3)
        assert inv.remove_items(0) == 0
        assert inv.remove_items(-5) == 0
        assert inv.quantity == 3  # Should not change

    def test_remove_items_from_empty_slot(self):
        """Test removing from empty slot."""
        inv = InventoryCellComponent()
        removed = inv.remove_items(1)
        assert removed == 0
        assert inv.quantity == 0

    def test_clear_slot(self):
        """Test clear_slot removes all items."""
        inv = InventoryCellComponent(max_stack_size=10)
        inv.add_items("sword", 5)
        previous = inv.clear_slot()
        assert previous == 5
        assert inv.quantity == 0
        assert inv.item_id is None

    def test_clear_slot_empty_slot(self):
        """Test clear_slot on empty slot."""
        inv = InventoryCellComponent()
        previous = inv.clear_slot()
        assert previous == 0
        assert inv.quantity == 0
        assert inv.item_id is None

    def test_inventory_component_with_equipped(self):
        """Test InventoryCellComponent with is_equipped flag."""
        inv = InventoryCellComponent(item_id="sword", quantity=1, is_equipped=True)
        assert inv.is_equipped is True

    def test_inventory_component_stacking(self):
        """Test stacking same items multiple times."""
        inv = InventoryCellComponent(max_stack_size=10)
        
        # Add in multiple steps
        assert inv.add_items("potion", 3) == 3
        assert inv.quantity == 3
        
        assert inv.add_items("potion", 4) == 4
        assert inv.quantity == 7
        
        assert inv.add_items("potion", 5) == 3  # Only 3 can fit
        assert inv.quantity == 10
        assert inv.is_full() is True

    def test_inventory_component_extra_fields(self):
        """Test InventoryCellComponent accepts extra fields."""
        inv = InventoryCellComponent(custom_data="test")
        assert inv.custom_data == "test"


class TestComponentIntegration:
    """Integration tests for component interactions."""

    def test_stat_component_with_editor_config(self):
        """Test StatComponent generates correct editor config."""
        stat = StatComponent(name="strength", base_value=10.0, min_value=0.0, max_value=20.0)
        config = stat.get_editor_config()
        
        assert "name" in config
        assert "base_value" in config
        assert "current_value" in config
        assert config["base_value"]["type"] == FieldType.NUMBER
        assert config["name"]["type"] == FieldType.TEXT

    def test_inventory_cell_component_with_editor_config(self):
        """Test InventoryCellComponent generates correct editor config."""
        inv = InventoryCellComponent(item_id="sword", quantity=1)
        config = inv.get_editor_config()
        
        assert "item_id" in config
        assert "quantity" in config
        assert "max_stack_size" in config
        assert config["quantity"]["type"] == FieldType.NUMBER
        assert config["item_id"]["type"] == FieldType.TEXT

    def test_component_model_serialization(self):
        """Test that components can be serialized to dict."""
        stat = StatComponent(name="health", base_value=100.0)
        data = stat.model_dump()
        
        assert data["name"] == "health"
        assert data["base_value"] == 100.0
        assert data["current_value"] == 100.0
        assert data["component_type"] == ComponentType.STAT

    def test_component_model_deserialization(self):
        """Test that components can be created from dict."""
        data = {
            "name": "mana",
            "base_value": 50.0,
            "current_value": 30.0,
            "component_type": "stat"
        }
        stat = StatComponent(**data)
        
        assert stat.name == "mana"
        assert stat.base_value == 50.0
        assert stat.current_value == 30.0


class TestInventoryComponent:
    """Tests for InventoryComponent (full inventory with multiple cells)."""

    def test_inventory_component_basic_creation(self):
        """Test basic InventoryComponent creation."""
        inv = InventoryComponent()
        assert inv.component_type == ComponentType.INVENTORY
        assert inv.cells == []
        assert inv.max_cells == 10
        assert inv.default_max_stack_size == 1

    def test_inventory_component_with_custom_settings(self):
        """Test InventoryComponent with custom settings."""
        inv = InventoryComponent(max_cells=20, default_max_stack_size=5)
        assert inv.max_cells == 20
        assert inv.default_max_stack_size == 5

    def test_add_item_to_empty_inventory(self):
        """Test adding item to empty inventory."""
        inv = InventoryComponent()
        added = inv.add_item("sword", 1)
        assert added == 1
        assert len(inv.cells) == 1
        assert inv.cells[0].item_id == "sword"
        assert inv.cells[0].quantity == 1

    def test_add_item_creates_new_cell(self):
        """Test adding item creates new cell."""
        inv = InventoryComponent(default_max_stack_size=5)
        added = inv.add_item("potion", 3)
        assert added == 3
        assert len(inv.cells) == 1
        assert inv.cells[0].item_id == "potion"
        assert inv.cells[0].quantity == 3

    def test_add_item_to_existing_cell(self):
        """Test adding item to existing cell with same item."""
        inv = InventoryComponent(default_max_stack_size=10)
        inv.add_item("potion", 5)
        added = inv.add_item("potion", 3)
        assert added == 3
        assert len(inv.cells) == 1
        assert inv.cells[0].quantity == 8

    def test_add_item_fills_existing_then_creates_new(self):
        """Test adding item fills existing cell then creates new."""
        inv = InventoryComponent(default_max_stack_size=5)
        inv.add_item("potion", 3)
        # Try to add 5 more (2 will fill existing, 3 will go to new cell)
        added = inv.add_item("potion", 5)
        assert added == 5
        assert len(inv.cells) == 2
        assert inv.cells[0].quantity == 5  # Filled to max
        assert inv.cells[1].quantity == 3   # Remaining items

    def test_add_item_different_items(self):
        """Test adding different items creates separate cells."""
        inv = InventoryComponent()
        inv.add_item("sword", 1)
        inv.add_item("axe", 1)
        assert len(inv.cells) == 2
        assert inv.cells[0].item_id == "sword"
        assert inv.cells[1].item_id == "axe"

    def test_add_item_respects_max_cells(self):
        """Test adding item respects max_cells limit."""
        inv = InventoryComponent(max_cells=2)
        inv.add_item("item1", 1)
        inv.add_item("item2", 1)
        added = inv.add_item("item3", 1)
        assert added == 0  # Can't add, max cells reached
        assert len(inv.cells) == 2

    def test_add_item_partial_add_when_full(self):
        """Test partial add when inventory is full."""
        inv = InventoryComponent(max_cells=2, default_max_stack_size=5)
        inv.add_item("potion", 5)
        inv.add_item("potion", 5)
        # Inventory has 2 full cells
        added = inv.add_item("potion", 3)
        assert added == 0  # Can't add more, all cells full and max_cells reached

    def test_remove_item_from_inventory(self):
        """Test removing item from inventory."""
        inv = InventoryComponent(default_max_stack_size=10)
        inv.add_item("potion", 5)
        removed = inv.remove_item("potion", 2)
        assert removed == 2
        assert inv.cells[0].quantity == 3

    def test_remove_item_from_multiple_cells(self):
        """Test removing item from multiple cells."""
        inv = InventoryComponent(default_max_stack_size=5)
        inv.add_item("potion", 5)
        inv.add_item("potion", 5)
        # Remove 7 items (5 from first cell, 2 from second)
        removed = inv.remove_item("potion", 7)
        assert removed == 7
        assert inv.cells[0].quantity == 0
        assert inv.cells[1].quantity == 3

    def test_remove_item_clears_cell(self):
        """Test removing all items clears the cell."""
        inv = InventoryComponent()
        inv.add_item("sword", 1)
        removed = inv.remove_item("sword", 1)
        assert removed == 1
        assert inv.cells[0].is_empty()

    def test_remove_item_partial_remove(self):
        """Test removing more than available removes what's available."""
        inv = InventoryComponent()
        inv.add_item("potion", 3)
        removed = inv.remove_item("potion", 10)
        assert removed == 3
        assert inv.cells[0].is_empty()

    def test_remove_item_nonexistent(self):
        """Test removing nonexistent item."""
        inv = InventoryComponent()
        removed = inv.remove_item("nonexistent", 1)
        assert removed == 0

    def test_has_item_true(self):
        """Test has_item returns True when item exists."""
        inv = InventoryComponent()
        inv.add_item("sword", 3)
        assert inv.has_item("sword") is True
        assert inv.has_item("sword", 2) is True
        assert inv.has_item("sword", 3) is True

    def test_has_item_false(self):
        """Test has_item returns False when item doesn't exist or insufficient quantity."""
        inv = InventoryComponent()
        assert inv.has_item("sword") is False
        inv.add_item("sword", 2)
        assert inv.has_item("sword", 3) is False

    def test_has_item_multiple_cells(self):
        """Test has_item checks across multiple cells."""
        inv = InventoryComponent(default_max_stack_size=5)
        inv.add_item("potion", 5)
        inv.add_item("potion", 3)
        assert inv.has_item("potion", 8) is True
        assert inv.has_item("potion", 9) is False

    def test_get_item_count(self):
        """Test get_item_count returns total quantity."""
        inv = InventoryComponent(default_max_stack_size=5)
        inv.add_item("potion", 5)
        inv.add_item("potion", 3)
        assert inv.get_item_count("potion") == 8

    def test_get_item_count_zero(self):
        """Test get_item_count returns 0 for nonexistent item."""
        inv = InventoryComponent()
        assert inv.get_item_count("nonexistent") == 0

    def test_get_empty_cells_count(self):
        """Test get_empty_cells_count returns correct count."""
        inv = InventoryComponent(max_cells=5)
        inv.add_item("item1", 1)
        inv.add_item("item2", 1)
        inv.add_item("item3", 1)
        # Remove from one cell
        inv.remove_item("item1", 1)
        assert inv.get_empty_cells_count() == 1  # One empty cell

    def test_is_full_true(self):
        """Test is_full returns True when all cells are full."""
        inv = InventoryComponent(max_cells=2, default_max_stack_size=5)
        inv.add_item("potion", 5)
        inv.add_item("potion", 5)
        assert inv.is_full() is True

    def test_is_full_false_partial(self):
        """Test is_full returns False when cells are not full."""
        inv = InventoryComponent(max_cells=2, default_max_stack_size=5)
        inv.add_item("potion", 3)
        assert inv.is_full() is False

    def test_is_full_false_not_all_cells(self):
        """Test is_full returns False when not all cells are used."""
        inv = InventoryComponent(max_cells=5, default_max_stack_size=5)
        inv.add_item("potion", 5)
        inv.add_item("potion", 5)
        assert inv.is_full() is False  # Only 2 of 5 cells used

    def test_clear_all(self):
        """Test clear_all clears all cells."""
        inv = InventoryComponent()
        inv.add_item("sword", 1)
        inv.add_item("axe", 1)
        inv.clear_all()
        assert all(cell.is_empty() for cell in inv.cells)

    def test_inventory_component_serialization(self):
        """Test InventoryComponent can be serialized."""
        inv = InventoryComponent(max_cells=5)
        inv.add_item("sword", 1)
        data = inv.model_dump()
        assert "cells" in data
        assert "max_cells" in data
        assert len(data["cells"]) == 1

