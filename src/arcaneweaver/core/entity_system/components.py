"""
ArcaneWeaver - Entity System Components Module.

This module defines the core Pydantic components used to build game entities
through composition without programming.
"""

__all__ = [
    "ComponentModel",
    "StatComponent",
    "StatsComponent",
    "InventoryCellComponent",
    "InventoryComponent",
    "ComponentType",
    "FieldType",
]

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from typing import Dict, List, Optional, Any, Union, get_origin, get_args
from enum import Enum
from pydantic.fields import FieldInfo


class FieldType(Enum):
    """Enumeration of supported field types for UI rendering."""

    NUMBER = "number"
    TEXT = "text"
    CHECKBOX = "checkbox"
    LIST = "list"
    OBJECT = "object"
    SELECT = "select"
    TEXTAREA = "textarea"


class ComponentType(Enum):
    """Enumeration of component types for categorization."""

    STAT = "stat"
    INVENTORY = "inventory"
    CUSTOM = "custom"


class ComponentModel(BaseModel):
    """Base class for all entity components.

    Provides common functionality for validation, serialization, and UI configuration
    generation. All game components should inherit from this class.

    Attributes:
        model_config: Pydantic configuration for extra field handling and validation.
        component_type: Type of component for categorization.
    """

    model_config = ConfigDict(extra="allow", validate_assignment=True, arbitrary_types_allowed=True)
    component_type: ComponentType = Field(default=ComponentType.CUSTOM, description="Component category")

    def get_editor_config(self) -> Dict[str, Any]:
        """Generates UI configuration from Pydantic model fields.

        Automatically creates editor configuration based on field types and
        validation rules. This enables dynamic form generation in the UI.

        Returns:
            Dictionary containing field configurations for UI rendering.
        """
        config = {}

        # Include defined fields
        for field_name, field_info in type(self).model_fields.items():
            if field_name == "component_type":
                continue  # Skip component_type field in editor

            field_config = {
                "type": self._infer_field_type(field_info),
                "label": field_name.replace("_", " ").title(),
                "description": field_info.description or "",
                "required": field_info.is_required(),
            }

            # Add field-specific constraints
            constraints = self._get_field_constraints(field_info)
            if constraints:
                field_config.update(constraints)

            config[field_name] = field_config

        # Include extra fields
        if self.model_extra:
            for field_name, field_value in self.model_extra.items():
                config[field_name] = {
                    "type": self._infer_value_type(field_value),
                    "label": field_name.replace("_", " ").title(),
                    "description": f"Dynamic attribute: {field_name}",
                    "required": False,
                }

        return config

    def _infer_field_type(self, field_info: FieldInfo) -> FieldType:
        """Infers UI field type from Pydantic field information.

        Args:
            field_info: Pydantic field information object.

        Returns:
            FieldType enum representing the UI field type.
        """
        annotation = field_info.annotation

        # Handle direct type checks
        if annotation is int or annotation is float:
            return FieldType.NUMBER
        elif annotation is str:
            return FieldType.TEXT
        elif annotation is bool:
            return FieldType.CHECKBOX
        elif annotation is list:
            return FieldType.LIST
        elif annotation is dict:
            return FieldType.OBJECT

        # Handle generic types (List, Optional, Union, etc.)
        origin = get_origin(annotation)
        if origin is not None:
            if origin is list:
                return FieldType.LIST
            elif origin is dict:
                return FieldType.OBJECT
            elif origin is Union:
                # Extract the inner type (Optional[T] is Union[T, None])
                args = get_args(annotation)
                if args:
                    # Filter out None type and get the first non-None type
                    non_none_args = [arg for arg in args if arg is not type(None)]
                    if non_none_args:
                        inner_annotation = non_none_args[0]
                        if inner_annotation is int or inner_annotation is float:
                            return FieldType.NUMBER
                        elif inner_annotation is str:
                            return FieldType.TEXT
                        elif inner_annotation is bool:
                            return FieldType.CHECKBOX

        # Default to text for unknown types
        return FieldType.TEXT

    def _infer_value_type(self, value: Any) -> FieldType:
        """Infers UI field type from a Python value.

        Args:
            value: Python value to analyze.

        Returns:
            FieldType enum representing the UI field type.
        """
        # Check bool first since bool is a subclass of int in Python
        if isinstance(value, bool):
            return FieldType.CHECKBOX
        elif isinstance(value, (int, float)):
            return FieldType.NUMBER
        elif isinstance(value, str):
            return FieldType.TEXT
        elif isinstance(value, list):
            return FieldType.LIST
        elif isinstance(value, dict):
            return FieldType.OBJECT
        else:
            return FieldType.TEXT

    def _get_field_constraints(self, field_info: FieldInfo) -> Dict[str, Any]:
        """Extracts validation constraints from Pydantic field.

        Args:
            field_info: Pydantic field information object.

        Returns:
            Dictionary of constraints for UI validation.
        """
        constraints = {}

        # Extract constraints from Field constraints (Pydantic v2 way)
        # Check for ge, gt, le, lt, min_length, max_length constraints
        if hasattr(field_info, "constraints") and field_info.constraints:
            constraints_dict = field_info.constraints
            if "ge" in constraints_dict:
                constraints["min"] = constraints_dict["ge"]
            if "gt" in constraints_dict:
                # For UI, we want inclusive min, so gt means min = gt + 1
                constraints["min"] = constraints_dict["gt"]
                constraints["exclusiveMin"] = True
            if "le" in constraints_dict:
                constraints["max"] = constraints_dict["le"]
            if "lt" in constraints_dict:
                # For UI, we want inclusive max, so lt means max = lt - 1
                constraints["max"] = constraints_dict["lt"]
                constraints["exclusiveMax"] = True
            if "min_length" in constraints_dict:
                constraints["minLength"] = constraints_dict["min_length"]
            if "max_length" in constraints_dict:
                constraints["maxLength"] = constraints_dict["max_length"]

        # Fallback: try to extract from metadata for compatibility
        if not constraints:
            metadata = getattr(field_info, "metadata", None) or []
            for meta_item in metadata:
                if isinstance(meta_item, dict):
                    if "ge" in meta_item:
                        constraints["min"] = meta_item["ge"]
                    if "le" in meta_item:
                        constraints["max"] = meta_item["le"]
                    if "gt" in meta_item:
                        constraints["min"] = meta_item["gt"]
                        constraints["exclusiveMin"] = True
                    if "lt" in meta_item:
                        constraints["max"] = meta_item["lt"]
                        constraints["exclusiveMax"] = True

        return constraints


class StatComponent(ComponentModel):
    """Component representing a single character statistic or attribute.

    Can be used for any entity (character, item, weapon, etc.) to represent
    a single numeric value with optional constraints and metadata.

    Attributes:
        name: Unique identifier for this statistic.
        base_value: The base numeric value of the statistic.
        current_value: The current modified value (defaults to base_value).
        min_value: Optional minimum constraint for the value.
        max_value: Optional maximum constraint for the value.
        description: Human-readable description of what this statistic represents.
    """

    component_type: ComponentType = Field(default=ComponentType.STAT, description="Component category")
    name: str = Field(..., description="Unique identifier for the statistic")
    base_value: float = Field(default=0.0, description="Base value of the statistic")
    current_value: float = Field(default=0.0, description="Current modified value")
    min_value: Optional[float] = Field(default=None, description="Minimum allowed value")
    max_value: Optional[float] = Field(default=None, description="Maximum allowed value")
    description: str = Field(default="", description="Description of what this statistic represents")

    def __init__(self, **data):
        """Initialize StatComponent with current_value defaulting to base_value."""
        if "current_value" not in data and "base_value" in data:
            data["current_value"] = data["base_value"]
        super().__init__(**data)

    @field_validator("current_value")
    @classmethod
    def validate_current_value(cls, current_value: float, validation_info) -> float:
        """Ensures current_value respects min_value and max_value constraints.

        Args:
            current_value: The current value to validate.
            validation_info: Validation context containing other field values.

        Returns:
            Validated current value, constrained within min/max bounds.
        """
        values = validation_info.data
        min_val = values.get("min_value")
        max_val = values.get("max_value")

        if min_val is not None and current_value < min_val:
            return min_val
        if max_val is not None and current_value > max_val:
            return max_val

        return current_value

    @field_validator("base_value")
    @classmethod
    def validate_base_value(cls, base_value: float, validation_info) -> float:
        """Ensures base_value respects min_value and max_value constraints.

        Args:
            base_value: The base value to validate.
            validation_info: Validation context containing other field values.

        Returns:
            Validated base value, constrained within min/max bounds.
        """
        values = validation_info.data
        min_val = values.get("min_value")
        max_val = values.get("max_value")

        if min_val is not None and base_value < min_val:
            return min_val
        if max_val is not None and base_value > max_val:
            return max_val

        return base_value

    def modify_value(self, modifier: float) -> float:
        """Applies a modifier to the current value.

        Args:
            modifier: The amount to add to the current value.

        Returns:
            The new current value after modification (constrained by min/max).
        """
        new_value = self.current_value + modifier
        
        # Apply constraints
        if self.min_value is not None and new_value < self.min_value:
            new_value = self.min_value
        if self.max_value is not None and new_value > self.max_value:
            new_value = self.max_value
        
        self.current_value = new_value
        return self.current_value

    def reset_to_base(self) -> None:
        """Resets the current value to the base value.
        
        Note: This will trigger validation automatically due to validate_assignment=True.
        """
        self.current_value = self.base_value

    def set_base_value(self, new_value: float) -> float:
        """Sets both base and current values to the new value.

        Args:
            new_value: The new value to set.

        Returns:
            The new base value after setting (constrained by min/max).
        """
        # Apply constraints before setting
        if self.min_value is not None and new_value < self.min_value:
            new_value = self.min_value
        if self.max_value is not None and new_value > self.max_value:
            new_value = self.max_value
        
        self.base_value = new_value
        self.current_value = new_value
        return self.base_value


class StatsComponent(ComponentModel):
    """Component representing a collection of statistics.

    Manages multiple StatComponent instances and provides high-level operations
    for adding, removing, and modifying statistics across the collection.

    Attributes:
        stats: List of StatComponent instances.
        max_stats: Maximum number of stats in this collection (None for unlimited).
    """

    component_type: ComponentType = Field(default=ComponentType.STAT, description="Component category")
    stats: List[StatComponent] = Field(default_factory=list, description="List of statistics")
    max_stats: Optional[int] = Field(default=None, ge=1, description="Maximum number of stats (None for unlimited)")

    @model_validator(mode="after")
    def validate_stats_count(self) -> "StatsComponent":
        """Ensures stats count doesn't exceed max_stats.

        Returns:
            The validated StatsComponent instance.
        """
        if self.max_stats is not None and len(self.stats) > self.max_stats:
            self.stats = self.stats[:self.max_stats]
        return self

    def add_stat(
        self,
        name: str,
        base_value: float = 0.0,
        current_value: Optional[float] = None,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        description: str = "",
        replace_if_exists: bool = False
    ) -> StatComponent:
        """Adds a new statistic to the collection.

        Args:
            name: Unique identifier for the statistic.
            base_value: Base value of the statistic (default: 0.0).
            current_value: Current value (defaults to base_value if not provided).
            min_value: Optional minimum constraint.
            max_value: Optional maximum constraint.
            description: Description of the statistic.
            replace_if_exists: If True, replaces existing stat with same name.

        Returns:
            The created or updated StatComponent instance.

        Raises:
            ValueError: If stat with same name already exists and replace_if_exists is False.
        """
        # Check if stat already exists
        existing_stat = self.get_stat(name)
        if existing_stat is not None:
            if replace_if_exists:
                self.remove_stat(name)
            else:
                raise ValueError(f"Stat with name '{name}' already exists. Use replace_if_exists=True to replace it.")

        # Check max_stats limit
        if self.max_stats is not None and len(self.stats) >= self.max_stats:
            raise ValueError(f"Cannot add stat: maximum number of stats ({self.max_stats}) reached")

        # Create new stat
        stat_data = {
            "name": name,
            "base_value": base_value,
            "min_value": min_value,
            "max_value": max_value,
            "description": description,
        }
        if current_value is not None:
            stat_data["current_value"] = current_value

        new_stat = StatComponent(**stat_data)
        self.stats.append(new_stat)
        return new_stat

    def remove_stat(self, name: str) -> bool:
        """Removes a statistic from the collection.

        Args:
            name: Name of the statistic to remove.

        Returns:
            True if statistic was found and removed, False otherwise.
        """
        for i, stat in enumerate(self.stats):
            if stat.name == name:
                del self.stats[i]
                return True
        return False

    def get_stat(self, name: str) -> Optional[StatComponent]:
        """Gets a statistic by name.

        Args:
            name: Name of the statistic to retrieve.

        Returns:
            StatComponent instance if found, None otherwise.
        """
        for stat in self.stats:
            if stat.name == name:
                return stat
        return None

    def has_stat(self, name: str) -> bool:
        """Checks if a statistic with the given name exists.

        Args:
            name: Name of the statistic to check.

        Returns:
            True if statistic exists, False otherwise.
        """
        return self.get_stat(name) is not None

    def modify_stat(self, name: str, modifier: float) -> Optional[float]:
        """Modifies the current value of a statistic.

        Args:
            name: Name of the statistic to modify.
            modifier: Amount to add to the current value.

        Returns:
            New current value if statistic was found and modified, None otherwise.
        """
        stat = self.get_stat(name)
        if stat is None:
            return None
        return stat.modify_value(modifier)

    def set_stat_base_value(self, name: str, new_value: float) -> Optional[float]:
        """Sets the base value of a statistic.

        Args:
            name: Name of the statistic.
            new_value: New base value to set.

        Returns:
            New base value if statistic was found, None otherwise.
        """
        stat = self.get_stat(name)
        if stat is None:
            return None
        return stat.set_base_value(new_value)

    def set_stat_current_value(self, name: str, new_value: float) -> Optional[float]:
        """Sets the current value of a statistic directly.

        Args:
            name: Name of the statistic.
            new_value: New current value to set.

        Returns:
            New current value if statistic was found, None otherwise.
        """
        stat = self.get_stat(name)
        if stat is None:
            return None
        stat.current_value = new_value
        return stat.current_value

    def reset_stat_to_base(self, name: str) -> bool:
        """Resets a statistic's current value to its base value.

        Args:
            name: Name of the statistic to reset.

        Returns:
            True if statistic was found and reset, False otherwise.
        """
        stat = self.get_stat(name)
        if stat is None:
            return False
        stat.reset_to_base()
        return True

    def reset_all_to_base(self) -> None:
        """Resets all statistics' current values to their base values."""
        for stat in self.stats:
            stat.reset_to_base()

    def get_stat_names(self) -> List[str]:
        """Gets a list of all statistic names.

        Returns:
            List of statistic names.
        """
        return [stat.name for stat in self.stats]

    def get_all_stats(self) -> List[StatComponent]:
        """Gets a copy of all statistics.

        Returns:
            List of all StatComponent instances.
        """
        return list(self.stats)

    def clear_all_stats(self) -> int:
        """Clears all statistics from the collection.

        Returns:
            Number of statistics that were cleared.
        """
        count = len(self.stats)
        self.stats.clear()
        return count


class InventoryCellComponent(ComponentModel):
    """Component representing a single inventory cell (slot) that can hold items.

    Models a single inventory cell with stackable items and capacity limits.
    Used by InventoryComponent to represent individual cells in an inventory.

    Attributes:
        item_id: Unique identifier of the item in this cell.
        quantity: Current number of items in the stack.
        max_stack_size: Maximum number of items that can be stacked.
        slot_type: Optional type restriction for items that can go in this cell.
        is_equipped: Whether this item is currently equipped (for equipment cells).
    """

    component_type: ComponentType = Field(default=ComponentType.INVENTORY, description="Component category")
    item_id: Optional[str] = Field(default=None, description="Unique identifier of the contained item")
    quantity: int = Field(default=0, ge=0, description="Current quantity of items in stack")
    max_stack_size: int = Field(default=1, ge=1, description="Maximum stack size")
    slot_type: Optional[str] = Field(default=None, description="Allowed item type for this slot")
    is_equipped: bool = Field(default=False, description="Whether this item is equipped")

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, quantity: int, validation_info) -> int:
        """Ensures quantity doesn't exceed max_stack_size.

        Args:
            quantity: The quantity value to validate.
            validation_info: Validation context containing other field values.

        Returns:
            Validated quantity, constrained by max_stack_size.
        """
        values = validation_info.data
        max_stack = values.get("max_stack_size", 1)

        if quantity > max_stack:
            return max_stack
        return quantity

    @model_validator(mode="after")
    def validate_item_id_and_quantity(self) -> "InventoryCellComponent":
        """Ensures logical consistency between item_id and quantity.

        Returns:
            The validated InventoryCellComponent instance.

        Raises:
            ValueError: If quantity is non-zero but no item_id is specified.
        """
        if self.quantity > 0:
            if self.item_id is None:
                raise ValueError("Cannot have quantity > 0 without an item_id")
        elif self.item_id is not None:
            # quantity == 0, so clear item_id
            self.item_id = None
        return self

    def is_empty(self) -> bool:
        """Checks if the inventory slot is empty.

        Returns:
            True if the slot contains no items, False otherwise.
        """
        return self.quantity == 0 or self.item_id is None

    def is_full(self) -> bool:
        """Checks if the inventory slot is at full capacity.

        Returns:
            True if the slot is at maximum stack size, False otherwise.
        """
        return self.quantity >= self.max_stack_size

    def add_items(self, item_id: str, add_quantity: int) -> int:
        """Adds items to the inventory slot.

        Args:
            item_id: The identifier of the items to add.
            add_quantity: The number of items to add.

        Returns:
            The number of items actually added (may be less due to stack limits).
        """
        if add_quantity <= 0:
            return 0

        # Check if we can add (different item in non-empty slot)
        if not self.is_empty() and self.item_id != item_id:
            return 0  # Can't add different items to the same slot

        available_space = self.max_stack_size - self.quantity
        actual_add = min(add_quantity, available_space)
        
        # Update using model_copy with update to ensure proper validation
        # This avoids validation errors when setting fields individually
        updated_data = {
            "item_id": item_id,
            "quantity": self.quantity + actual_add,
        }
        updated = self.model_copy(update=updated_data)
        # Copy all validated fields back to self
        self.__dict__.update(updated.__dict__)

        return actual_add

    def remove_items(self, remove_quantity: int) -> int:
        """Removes items from the inventory slot.

        Args:
            remove_quantity: The number of items to remove.

        Returns:
            The number of items actually removed.
        """
        if remove_quantity <= 0 or self.is_empty():
            return 0

        actual_remove = min(remove_quantity, self.quantity)
        new_quantity = self.quantity - actual_remove
        
        # Update using model_copy with update to ensure proper validation
        updated_data = {"quantity": new_quantity}
        if new_quantity == 0:
            updated_data["item_id"] = None
        
        updated = self.model_copy(update=updated_data)
        # Copy all validated fields back to self
        self.__dict__.update(updated.__dict__)

        return actual_remove

    def clear_slot(self) -> int:
        """Completely clears the inventory cell.

        Returns:
            The number of items that were in the cell before clearing.
        """
        previous_quantity = self.quantity
        # Set quantity to 0 first to avoid validation error
        self.quantity = 0
        self.item_id = None
        return previous_quantity


class InventoryComponent(ComponentModel):
    """Component representing a full inventory with multiple cells.

    Manages a collection of inventory cells and provides high-level operations
    for adding, removing, and checking items across the entire inventory.

    Attributes:
        cells: List of inventory cells that can hold items.
        max_cells: Maximum number of cells in this inventory.
        default_max_stack_size: Default maximum stack size for new cells.
    """

    component_type: ComponentType = Field(default=ComponentType.INVENTORY, description="Component category")
    cells: List[InventoryCellComponent] = Field(default_factory=list, description="List of inventory cells")
    max_cells: int = Field(default=10, ge=1, description="Maximum number of cells in inventory")
    default_max_stack_size: int = Field(default=1, ge=1, description="Default max stack size for new cells")

    @model_validator(mode="after")
    def validate_cells_count(self) -> "InventoryComponent":
        """Ensures cells count doesn't exceed max_cells.

        Returns:
            The validated InventoryComponent instance.
        """
        if len(self.cells) > self.max_cells:
            self.cells = self.cells[:self.max_cells]
        return self

    def add_item(self, item_id: str, quantity: int = 1, max_stack_size: Optional[int] = None) -> int:
        """Adds items to the inventory.

        Tries to add to existing cells with the same item_id first,
        then adds to empty cells if space is available.

        Args:
            item_id: The identifier of the item to add.
            quantity: The number of items to add (default: 1).
            max_stack_size: Optional max stack size for new cells (uses default if not provided).

        Returns:
            The number of items actually added (may be less if inventory is full).
        """
        if quantity <= 0:
            return 0

        remaining_quantity = quantity

        # First, try to add to existing cells with the same item
        for cell in self.cells:
            if not cell.is_empty() and cell.item_id == item_id:
                added = cell.add_items(item_id, remaining_quantity)
                remaining_quantity -= added
                if remaining_quantity <= 0:
                    return quantity

        # Then, try to add to empty cells
        while remaining_quantity > 0:
            # Find an empty cell
            empty_cell = None
            for cell in self.cells:
                if cell.is_empty():
                    empty_cell = cell
                    break

            # If no empty cell exists and we can create new cells, create one
            if empty_cell is None and len(self.cells) < self.max_cells:
                stack_size = max_stack_size if max_stack_size is not None else self.default_max_stack_size
                new_cell = InventoryCellComponent(max_stack_size=stack_size)
                self.cells.append(new_cell)
                empty_cell = new_cell

            # If we have an empty cell, add items to it
            if empty_cell is not None:
                added = empty_cell.add_items(item_id, remaining_quantity)
                remaining_quantity -= added
            else:
                # No more space available
                break

        return quantity - remaining_quantity

    def remove_item(self, item_id: str, quantity: int = 1) -> int:
        """Removes items from the inventory.

        Removes items from cells containing the specified item_id,
        starting from the first cell with that item.

        Args:
            item_id: The identifier of the item to remove.
            quantity: The number of items to remove (default: 1).

        Returns:
            The number of items actually removed.
        """
        if quantity <= 0:
            return 0

        remaining_to_remove = quantity

        # Remove from cells containing this item
        for cell in self.cells:
            if not cell.is_empty() and cell.item_id == item_id:
                removed = cell.remove_items(remaining_to_remove)
                remaining_to_remove -= removed
                if remaining_to_remove <= 0:
                    return quantity

        return quantity - remaining_to_remove

    def has_item(self, item_id: str, quantity: int = 1) -> bool:
        """Checks if the inventory contains at least the specified quantity of an item.

        Args:
            item_id: The identifier of the item to check.
            quantity: The minimum quantity to check for (default: 1).

        Returns:
            True if the inventory contains at least the specified quantity, False otherwise.
        """
        if quantity <= 0:
            return True

        total_quantity = 0
        for cell in self.cells:
            if not cell.is_empty() and cell.item_id == item_id:
                total_quantity += cell.quantity
                if total_quantity >= quantity:
                    return True

        return False

    def get_item_count(self, item_id: str) -> int:
        """Gets the total quantity of a specific item in the inventory.

        Args:
            item_id: The identifier of the item to count.

        Returns:
            The total quantity of the item across all cells.
        """
        total = 0
        for cell in self.cells:
            if not cell.is_empty() and cell.item_id == item_id:
                total += cell.quantity
        return total

    def get_empty_cells_count(self) -> int:
        """Gets the number of empty cells in the inventory.

        Returns:
            The number of empty cells.
        """
        return sum(1 for cell in self.cells if cell.is_empty())

    def is_full(self) -> bool:
        """Checks if the inventory is full (all cells are occupied and at max capacity).

        Returns:
            True if all cells are full, False otherwise.
        """
        if len(self.cells) < self.max_cells:
            return False

        for cell in self.cells:
            if not cell.is_full():
                return False

        return True

    def clear_all(self) -> None:
        """Clears all cells in the inventory."""
        for cell in self.cells:
            cell.clear_slot()
