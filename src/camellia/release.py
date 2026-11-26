from beet import Context


def beet_default(ctx: Context):
	"""Package data and resource packs for release"""
	version = f"v{ctx.project_version}"
	name: str = getattr(ctx, 'project_name', None) or ctx.project_id

	# datapack
	dp_path = ctx.directory / "build" / f"{name}-dp-{version}"
	ctx.data.save(path=dp_path, overwrite=True, zipped=True)

	# resourcepack
	rp_path = ctx.directory / "build" / f"{name}-rp-{version}"
	ctx.assets.save(path=rp_path, overwrite=True, zipped=True)
