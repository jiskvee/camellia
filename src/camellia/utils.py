from __future__ import annotations

from beet import Context, ItemModel, Model


class Location:
	"""Represents a resource location, allowing to define stuff like `function this.use`"""

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


def technical(path: str) -> str:
	path = str(path)
	sep = ":"
	insert = "technical/"
	if sep in path:
		prefix, rest = path.split(sep, 1)
		if not rest.startswith(insert):
			return f"{prefix}{sep}{insert}{rest}"
	return path


def simple_model(ctx: Context, id:str, parent:str = "generated"):
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
	return f'{b}[minecraft:custom_data~{{{NS}:{{id:{ID}}}}}]'


def in_bundle(NS:str, ID:str) -> str:
	# #bundles[bundle_contents~{items:{contains:[{predicates:{custom_data:{jisk:{}}}}]}}]
	return f'#bundles[bundle_contents~{{items:{{contains:[{{predicates:{{custom_data:{{{NS}:{{id:{ID}}}}}}}}}]}}}}]'


def trinket(NS:str, ID:str) -> str:
	return f'#bundles[custom_data~{{thallium:{{id:"trinket_pouch",equipped:true}}}},bundle_contents~{{items:{{contains:[{{predicates:{{custom_data:{{{NS}:{{id:{ID}}}}}}}}}]}}}}]'
	#execute if items entity @s container.* #minecraft:bundles[minecraft:custom_data~{thallium:{id:"trinket_pouch",equipped:true}},minecraft:bundle_contents~{items:{contains:[{predicates:{"minecraft:custom_data":{recondite:{id:"carnal_singularity"}}}}]}}] run say yummers!
	'''
	execute if items entity @s container.* #minecraft:bundles[
		minecraft:custom_data~{
			thallium:{
				id:"trinket_pouch",
				equipped:true
			}
		},
		minecraft:bundle_contents~{
			items:{
				contains:[
					{
						predicates:{
							"minecraft:custom_data":{
								recondite:{
									id:"carnal_singularity"
								}
							}
						}
					}
				]
			}
		}
	] run say yummers!
	'''
