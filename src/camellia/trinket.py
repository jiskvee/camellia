from copy import deepcopy
from typing import Any, ClassVar

from beet import Context, FileDeserialize, JsonFileBase, LootTable, NamespaceFileScope
from beet.core.utils import TextComponent
from pydantic import BaseModel, ConfigDict


class Display(BaseModel):
	model_config = ConfigDict(populate_by_name=True)
	
	pack_mark: TextComponent | None = None
	trinket_icon: TextComponent | None = None

class Trinket(BaseModel):
	model_config = ConfigDict(populate_by_name=True)
	
	id: str
	rarity: str = "common"
	weight_percent: int | None = None
	max_stack_size: int | None = None
	
	tooltip_style: str | None = None
	item_model: str = "thallium:thallium_ingot"
	description: list[TextComponent] = []
	display: Display = Display()

class TrinketFile(JsonFileBase[Trinket]):
	model = Trinket
	scope: ClassVar[NamespaceFileScope] = ("trinket",)
	extension: ClassVar[str] = ".json"
	data: ClassVar[FileDeserialize[Trinket]] = FileDeserialize()

def clean_lore_component(component: Any) -> Any:
	"""
	Recursively removes 'pouch_color' from the component structure.
	"""
	if isinstance(component, dict):
		if "pouch_color" in component:
			del component["pouch_color"]
		return component
	elif isinstance(component, list):
		return [clean_lore_component(item) for item in component]
	return component

def process_pouch_component(component: Any) -> Any:
	"""
	Recursively applies pouch color logic.
	- If dict: uses 'pouch_color' if present, else defaults to green. Overwrites 'color'.
	- If str: converts to dict with default green.
	- If list: recurses on elements.
	"""
	default_color = "#6caf3e"

	if isinstance(component, dict):
		target_color = default_color
		if "pouch_color" in component:
			target_color = component["pouch_color"]
			del component["pouch_color"]
		
		component["color"] = target_color
		return component
	
	elif isinstance(component, list):
		return [process_pouch_component(item) for item in component]
	
	elif isinstance(component, str):
		return {"text": component, "color": default_color}
		
	return component

def create_loot_table(namespace: str, trinket: Trinket) -> dict[str, Any]:
	"""
	Generates the loot table dictionary based on the Trinket definition.
	"""
	
	# --- 1. Calculate Weight and Stack Size ---
	final_weight = 10
	final_stack_size = 10

	if trinket.weight_percent is not None and trinket.max_stack_size is not None:
		final_weight = trinket.weight_percent
		final_stack_size = trinket.max_stack_size
		
	elif trinket.weight_percent is not None:
		final_weight = trinket.weight_percent
		if final_weight > 0:
			raw_stack = 100 / final_weight
			final_stack_size = int(raw_stack)
			if raw_stack % 1 != 0:
				print(f"[WARNING] Trinket '{trinket.id}': Weight {final_weight}% results in fractional stack size ({raw_stack}). Rounding down to {final_stack_size}.")
		else:
			final_stack_size = 1
			
	elif trinket.max_stack_size is not None:
		final_stack_size = trinket.max_stack_size
		if final_stack_size > 0:
			final_weight = int(100 / final_stack_size)
		else:
			final_weight = 0
			
	else:
		final_weight = 10
		final_stack_size = 10

	# --- 2. Process Descriptions ---
	lore_description = []
	pouch_description = []

	for line in trinket.description:
		# Prepare Lore Line (Standard display)
		# Deepcopy to ensure we don't mutate the original pydantic model in place during iteration
		lore_line = deepcopy(line)
		lore_line = clean_lore_component(lore_line)
		lore_description.append(lore_line)

		# Prepare Pouch Line (Green/Custom display)
		pouch_line = deepcopy(line)
		pouch_line = process_pouch_component(pouch_line)
		pouch_description.append(pouch_line)

	# --- 3. Build Lore List ---
	lore_list = []
	
	if trinket.display.pack_mark:
		lore_list.append(trinket.display.pack_mark)

	lore_list.extend([
		{
			"translate": "item.thallium.trinket.description",
			"italic": False,
			"color": "gray",
			"with": [
				{
					"translate": "item.thallium.trinket_pouch",
					"color": "#a9dd52"
				}
			]
		},
		{
			"translate": "item.thallium.trinket.weight",
			"color": "#6caf3e",
			"italic": False,
			"with": [
				str(final_weight)
			]
		},
		"",
		{
			"translate": "item.thallium.trinket.header",
			"color": "#a9dd52",
			"italic": False
		}
	])
	
	lore_list.extend(lore_description)

	# --- 4. Build Components Dictionary ---
	components = {
		"!minecraft:consumable": {},
		"minecraft:rarity": trinket.rarity,
		"minecraft:item_model": trinket.item_model,
		"minecraft:max_stack_size": final_stack_size,
		"minecraft:item_name": {
			"translate": f"item.{namespace}.{trinket.id}"
		},
		"minecraft:lore": lore_list
	}

	if trinket.tooltip_style:
		components["minecraft:tooltip_style"] = trinket.tooltip_style

	# --- 5. Build Tooltip Header ---
	tooltip_header = []
	if trinket.display.trinket_icon:
		tooltip_header.append(trinket.display.trinket_icon)
	
	tooltip_header.extend([
		{
			"translate": f"item.{namespace}.{trinket.id}",
			"font": "minecraft:default",
			"color": "yellow",
			"italic": False
		},
		{
			"text": f" ({final_weight}%)",
			"font": "minecraft:default",
			"color": "dark_gray",
			"italic": False
		}
	])

	# --- 6. Add Custom Data ---
	components["minecraft:custom_data"] = {
		namespace: {
			"id": trinket.id
		},
		"thallium": {
			"trinket": {
				"tooltip": [
					tooltip_header,
					*pouch_description
				]
			}
		},
		"smithed": {
			"ignore": {
				"functionality": True,
				"crafting": True
			}
		}
	}

	# --- 7. Construct Final Loot Table ---
	return {
		"pools": [
			{
				"rolls": 1,
				"entries": [
					{
						"type": "minecraft:item",
						"name": "minecraft:poisonous_potato",
						"functions": [
							{
								"function": "minecraft:set_components",
								"components": components
							},
							{
								"function": "minecraft:copy_custom_data",
								"source": {
									"type": "minecraft:storage",
									"source": "thallium:storage"
								},
								"ops": [
									{
										"source": "root.random",
										"target": "thallium.unique_id",
										"op": "replace"
									}
								]
							}
						]
					}
				]
			}
		]
	}

def load_trinkets(ctx: Context):
	ctx.data.extend_namespace.append(TrinketFile)
	yield
	ctx.data[TrinketFile].clear()

def beet_default(ctx: Context):
	for path, file in ctx.data[TrinketFile].items():
		trinket_data = file.data

		if isinstance(trinket_data, dict):
			trinket_data = Trinket(**trinket_data)

		namespace = ctx.project_id if ctx.project_id else "camellia"

		loot_table_data = create_loot_table(namespace, trinket_data)
		
		name = str(path).split(":")[1]
		ctx.data.loot_tables[f"{namespace}:items/{name}"] = LootTable(loot_table_data)
