from beet import Context, Recipe, LootTable, Model, ItemModel, Equipment, FileDeserialize, JsonFileBase, NamespaceFileScope
from beet.core.utils import TextComponent
from typing import Any, ClassVar
from pydantic import BaseModel


class Item(BaseModel):
	id: str
	name: TextComponent
	description: str | list[TextComponent] = []

	base_item: str
	components: dict[str, Any] = {}
	smithed_ignore: dict[str, bool] | None = None

	category: str | None = None
	recipe: dict | str | None = None
	recipe_adv: dict | str | None = None

	model: dict | str | None = None
	definition: dict | str | None = None
	parent_model: str = "item/generated"
	equipment_layers: dict | str | None = None


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

	for location, file in ctx.data[ItemFile].items():
		item = file.data
		ns, path = location.split(":", 1)
		print(f"Creating item {location}\n{item}")

		# lore
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

		# equipment sssss
		if item.equipment_layers is not None:
			if isinstance(item.equipment_layers, str): # single texture
				ctx.assets.equipments[location] = Equipment({
					"layers": {
						item.equipment_layers: [{"texture": location}]
					}
				})
			else: # inline
				ctx.assets.equipments[location] = Equipment(item.equipment_layers)


		# model
		if isinstance(item.model, str): # location
			resolved_model = item.model
		else:
			resolved_model = f"{ns}:item/{path}"
			if item.model is not None: # inline
				ctx.assets.models[resolved_model] = Model(item.model)
			else: # omitted
				ctx.assets.models[resolved_model] = Model({
					"parent": item.parent_model,
					"textures": {
						"layer0": resolved_model
					}
				})

		# definition
		if isinstance(item.definition, str): # location
			resolved_definition = item.definition
		else:
			resolved_definition = location
			if item.definition is not None: # inline
				ctx.assets.item_models[resolved_definition] = ItemModel(item.definition)
			else: # omitted
				ctx.assets.item_models[resolved_definition] = ItemModel({
					"model": {
						"type": "model",
						"model": resolved_model
					}
				})

		# final components
		resolved_components: dict[str, Any] = {
			"minecraft:item_name": item.name,
			"minecraft:item_model": resolved_definition,
			"minecraft:lore": resolved_lore,
			"minecraft:custom_data": {
				ns: { "id": item.id },
				**({"smithed": item.smithed_ignore} if item.smithed_ignore is not None else {})
			},
			**item.components
		}

		# build loot table
		ctx.data.loot_tables[f"{ns}:items/{path}"] = LootTable({
			"pools": [{
				"rolls": 1,
				"entries": [{
					"type": "minecraft:item",
					"name": item.base_item,
					"functions": [{
						"function": "minecraft:set_components",
						"components": resolved_components
					}]
				}]
			}]
		})

		# parse recipe field
		if item.recipe is None: # omitted
			return
		elif isinstance(item.recipe, str): # location
			resolved_recipe = ctx.data.recipes[item.recipe].data
		else: # inline
			resolved_recipe = item.recipe

		# build recipe
		current_result: dict = resolved_recipe.get("result", {})
		new_data: dict[str, Any] = {
			"id": item.base_item,
			"components": resolved_components
		}
		if isinstance(current_result, str):
			current_result = new_data
		resolved_recipe["result"] = current_result | new_data

		cat = f"{item.category}/" if item.category is not None else ""
		ctx.data.recipes[f"{ns}:{cat}{item.id}"] = Recipe(resolved_recipe)
