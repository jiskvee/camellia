from typing import ClassVar

from beet import (
	Advancement,
	Context,
	Equipment,
	FileDeserialize,
	ItemModel,
	JsonFileBase,
	LootTable,
	Model,
	NamespaceFileScope,
	Recipe,
)
from beet.core.utils import JsonDict, TextComponent
from pydantic import BaseModel

from .unjank import CreativeTab, ItemSource


class Item(BaseModel):
	id: str
	base_item: str = "minecraft:poisonous_potato"

	name: TextComponent
	description: str | list[TextComponent] = []
	tooltip_style: str | None = None
	custom_data: JsonDict = {}
	components: JsonDict = {}
	extra_modifier: JsonDict | str | list[JsonDict|str] | None = None

	category: str | None = None
	recipe: JsonDict | str | None = None
	recipe_advancement: JsonDict | str | None = None

	model: JsonDict | str | None = None
	definition: JsonDict | str | None = None
	parent_model: str = "item/generated"
	equipment_layers: JsonDict | str | None = None


class ItemFile(JsonFileBase[Item]):
	data: ClassVar[FileDeserialize[Item]] = FileDeserialize()
	scope: ClassVar[NamespaceFileScope] = ("item",)
	extension: ClassVar[str] = ".json"
	model = Item


def load_items(ctx: Context):
	ctx.data.extend_namespace.append(ItemFile)
	yield
	ctx.data[ItemFile].clear()


def beet_default(ctx: Context):
	if not ctx.data[ItemFile]:
		print("Warning: No items found.")
		return

	autoadd = False
	tab: JsonDict|None = None
	creative_tabs = ctx.data[CreativeTab]
	if creative_tabs:
		config: dict = ctx.meta.get("camellia", {}).get("creative_tab", {})
		tab_id: str = config.get("id", "")
		autoadd: bool = config.get("auto_add", False)
		if tab_id != "" and (entry := creative_tabs.get(tab_id)) is not None:
			tab = entry.data

	for location, file in ctx.data[ItemFile].items():
		generate_item(ctx, location, file, tab, autoadd)


def generate_item(ctx: Context, location: str, file: ItemFile, creative_tab: JsonDict|None, autoadd:bool):
	item = file.data
	ns, path = location.split(":", 1)
	#print(f"Creating item {location}\n{item}")

	# only create equipment file, up to the user to define how it's used since it's pretty specific
	if item.equipment_layers is not None:
		if isinstance(item.equipment_layers, str): # single texture
			ctx.assets.equipments[location] = Equipment({
				"layers": {
					item.equipment_layers: [{"texture": location}]
				}
			})
		else: # inline
			ctx.assets.equipments[location] = Equipment(item.equipment_layers)

	# parse lore
	if isinstance(item.description, str):
		resolved_lore: list[TextComponent] = [{
			"text": item.description,
			"color": "gray",
			"italic": False
		}]
	elif isinstance(item.description, list) and all(isinstance(line, str) for line in item.description):
		resolved_lore: list[TextComponent] = [
			{
				"text": line,
				"color": "gray",
				"italic": False
			}
			for line in item.description
		]
	else:
		resolved_lore: list[TextComponent] = item.description

	# model and definition
	if isinstance(item.definition, str) and item.definition.startswith("minecraft"):
		resolved_definition = item.definition
	else:
		resolved_model: str = resolve_model(ctx, item, ns, path)
		resolved_definition: str = resolve_definition(ctx, item, resolved_model, location)

	# base custom data
	base_data: JsonDict = {
		ns: { "id": item.id },
		"smithed": { "ignore": { "functionality": True, "crafting": True } }
	}

	# final components
	resolved_components: JsonDict = {
		"minecraft:item_name": item.name,
		"minecraft:item_model": resolved_definition,
		**({"minecraft:tooltip_style": item.tooltip_style} if item.tooltip_style is not None else {}),
		"minecraft:lore": resolved_lore,
		"minecraft:custom_data": recursive_merge(base_data, item.custom_data),
		**item.components
	}

	# modifier list
	modifiers: list = [{
		"type": "minecraft:set_components",
		"components": resolved_components
	}]
	if item.extra_modifier:
		if isinstance(item.extra_modifier, list):
			modifiers.extend(item.extra_modifier)
		else:
			modifiers.append(item.extra_modifier)

	# build loot table
	loot_path = f"{ns}:items/{path}"
	source_path = f"{ns}:{path}"
	ctx.data.loot_tables[loot_path] = LootTable({
		"pools": [{
			"rolls": 1,
			"entries": [{
				"type": "minecraft:item",
				"name": item.base_item,
				"modifier": modifiers
			}]
		}]
	})
	if creative_tab:
		ctx.data[ItemSource][source_path] = ItemSource({
			"type": "unjank:loot",
			"loot": loot_path
		})
		if autoadd: creative_tab["items"].append(source_path)

	# parse recipe field
	if item.recipe is None: # omitted
		return
	elif isinstance(item.recipe, str): # location
		resolved_recipe = ctx.data.recipes[item.recipe].data
	else: # inline
		resolved_recipe = item.recipe

	# build recipe
	current_result: JsonDict = resolved_recipe.get("result", {})
	new_data: JsonDict = {
		"id": item.base_item,
		"components": resolved_components
	}
	if isinstance(current_result, str):
		current_result = new_data
	resolved_recipe["result"] = current_result | new_data

	cat = f"{item.category}/" if item.category is not None else ""
	recipe_path = f"{ns}:{cat}{item.id}"
	ctx.data.recipes[recipe_path] = Recipe(resolved_recipe)

	# parse recipe advancement
	if item.recipe_advancement is None or isinstance(item.recipe_advancement, str): # omitted or location
		return
	else: # inline
		item.recipe_advancement["rewards"] = { "recipes": [recipe_path] }
		ctx.data.advancements[f"{ns}:recipes/{cat}{item.id}"] = Advancement(item.recipe_advancement)


def resolve_model(ctx: Context, item: Item, ns: str, path: str) -> str:
	if isinstance(item.model, str): # location
		moodel = item.model
	else:
		moodel = f"{ns}:item/{path}"
		if item.model is not None: # inline
			ctx.assets.models[moodel] = Model(item.model)
		elif item.definition is None: # omitted, and no definition provided
			ctx.assets.models[moodel] = Model({
				"parent": item.parent_model,
				"textures": {
					"layer0": moodel
				}
			})
	return moodel


def resolve_definition(ctx: Context, item: Item, resolved_model: str, location: str) -> str:
	if isinstance(item.definition, str): # location
		definitive = item.definition
	else:
		definitive = location
		if item.definition is not None: # inline
			ctx.assets.item_models[definitive] = ItemModel(item.definition)
		else: # omitted
			ctx.assets.item_models[definitive] = ItemModel({
				"model": {
					"type": "model",
					"model": resolved_model
				}
			})
	return definitive


def recursive_merge(dict1, dict2):
    for key, value in dict2.items():
        if key in dict1 and isinstance(dict1[key], dict) and isinstance(value, dict):
            # Recursively merge nested dictionaries
            dict1[key] = recursive_merge(dict1[key], value)
        else:
            # Merge non-dictionary values
            dict1[key] = value
    return dict1
