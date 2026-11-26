from __future__ import annotations

from beet import Context, FunctionTag, ItemModel, Model


class Location:
	"""Represents a resource location, letting you define stuff like `function this.use`"""

	__slots__ = ('path',)

	def __init__(self, path: str):
		self.path: str = path
	
	def __str__(self) -> str:
		return self.path

	def __repr__(self) -> str:
		return f"Location('{self.path}')"

	def __getattr__(self, name: str) -> Location:
		if name.startswith('__'):
			raise AttributeError(name)
		return Location(f'{self.path}/{name}')
		#return f'{self.path}/{name}'

	def __call__(self) -> str:
		return self.path


def merge_func_tag(ctx: Context, tag: str, value: str):
	"""Adds a value to function tag if it exists, or creates it otherwise"""
	ctx.data.function_tags.merge({
		tag: FunctionTag({"values": [
			{"id": value, "required": False}
		]})
	})


def technical(path: str) -> str:
	"""Inserts `technical` after the namespace in a resource location"""
	path = str(path)
	sep = ":"
	insert = "technical/"
	if sep in path:
		prefix, rest = path.split(sep, 1)
		if not rest.startswith(insert):
			return f"{prefix}{sep}{insert}{rest}"
	return path


def simple_model(ctx: Context, id:str, parent:str = "generated"):
	"""Creates a simple model and item definition"""
	ns = ctx.project_id
	tex = f"{ns}:item/{id}"
	ctx.assets.item_models[f"{ns}:{id}"] = ItemModel({
		"model": {
			"type": "model",
			"model": tex
		}
	})
	ctx.assets.models[f"{ns}:item/{id}"] = Model({
		"parent": f"minecraft:item/{parent}",
		"textures": {
			"layer0": tex
		}
	})


def cit(NS:str, ID:str, b:str = '*') -> str:
	"""Check for an item with an id in namespaced custom data"""
	return f'{b}[custom_data~{{{NS}:{{id:{ID}}}}}]'


def in_bundle(NS:str, ID:str) -> str:
	"""Checks for an item inside a bundle"""
	return f'#bundles[bundle_contents~{{items:{{contains:[{{predicates:{{custom_data:{{{NS}:{{id:{ID}}}}}}}}}]}}}}]'
	# #bundles[bundle_contents~{items:{contains:[{predicates:{custom_data:{jisk:{}}}}]}}]


def trinket(NS:str, ID:str) -> str:
	"""Checks for a specific trinket inside an equipped Thallium trinket pouch"""
	return f'#bundles[custom_data~{{thallium:{{id:"trinket_pouch",equipped:true}}}},bundle_contents~{{items:{{contains:[{{predicates:{{custom_data:{{{NS}:{{id:{ID}}}}}}}}}]}}}}]'
	# #bundles[custom_data~{thallium:{id:"trinket_pouch",equipped:true}},bundle_contents~{items:{contains:[{predicates:{"custom_data":{recondite:{id:"carnal_singularity"}}}}]}}]
