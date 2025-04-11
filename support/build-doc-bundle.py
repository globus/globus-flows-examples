#!/usr/bin/env -S pipx run

# /// script
# requires-python = ">=3.9"
# dependencies = ["click", "jinja2", "pyyaml"]
# ///

from __future__ import annotations

import dataclasses
import glob
import io
import os
import tarfile
import textwrap
import typing as t

try:
    import click
    import jinja2
    import yaml
except ModuleNotFoundError:
    print(
        """\
library imports failed in 'build-doc-bundle.py'

Did you try to run the script with 'python build-doc-bundle.py'?
Use 'pipx run build-doc-bundle.py' or './build-doc-bundle.py' instead!
""",
        end="",
    )
    raise SystemExit(1)


@click.option(
    "-o",
    "--output",
    default="doc_bundle.tar.gz",
    type=click.Path(writable=True, dir_okay=False, resolve_path=True),
    help="Output filename.",
)
@click.command
def main(output: str):
    click.echo("Bundling examples for docs.globus.org", err=True)
    go_to_repo_root()

    with tarfile.open(output, "w:gz") as archive:
        for filename, file_bytes in build_all_files():
            file_info = tarfile.TarInfo(filename)
            file_info.size = len(file_bytes)
            archive.addfile(file_info, io.BytesIO(file_bytes))

    click.echo(f"Done. Output is available at {output}")


def build_all_files():
    all_example_configs: list[ExampleDocBuildConfig] = []
    for config_filename in find_build_configs():
        example_dir = os.path.dirname(config_filename)
        click.echo(f"building for {example_dir}", err=True)

        config = load_config(config_filename)
        all_example_configs.append(config)

        if not config.readme_is_index:
            click.echo(
                "doc builds currently only support readme_is_index behavior",
                err=True,
            )
            raise click.Abort()

        for sub_path in ("definition.json", "input_schema.json", "sample_input.json"):
            with open(os.path.join(example_dir, sub_path), "rb") as fp:
                yield f"{config.example_dir}/{sub_path}", fp.read()
        with open(os.path.join(example_dir, "README.adoc"), "rb") as fp:
            content = fp.read()
            if config.append_source_blocks:
                content = append_source_blocks(content)
            content = prepend_preamble(config, content)
            yield f"{config.example_dir}/index.adoc", content
    yield "index.adoc", build_index_doc(all_example_configs)


def go_to_repo_root():
    support_dir = os.path.dirname(__file__)
    os.chdir(os.path.dirname(support_dir))


def find_build_configs():
    for item in glob.glob("*/**/.doc_config.yaml"):
        yield item


def prepend_preamble(config: ExampleDocBuildConfig, content: bytes) -> bytes:
    return (
        textwrap.dedent(
            f"""\
            ---
            menu_weight: {config.menu_weight}
            ---

            """
        ).encode("utf-8")
        + content
    )


def append_source_blocks(content: bytes) -> bytes:
    return (
        content
        + textwrap.dedent(
            """
            == Source code

            [.accordionize]
            --
            .Definition
            [%collapsible]
            ====
            [source,json,role=clippable-code]
            ----
            include::definition.json[]
            ----
            ====
            --

            [.accordionize]
            --
            .Input Schema
            [%collapsible]
            ====
            [source,json,role=clippable-code]
            ----
            include::input_schema.json[]
            ----
            ====
            --

            [.accordionize]
            --
            .Example Input
            [%collapsible]
            ====
            [source,json]
            ----
            include::sample_input.json[]
            ----
            ====
            --
            """
        ).encode("utf-8")
    )


INDEX_TEMPLATE = jinja2.Template(
    """\
---
menu_weight: 180
---
[#flows-intro-examples]
= Example Flows

{% for item in examples %}
link:{{ item.example_dir }}/[{{ item.title }}]::
+
{{ item.short_description | indent(first=True) | replace("\n\n", "\n+\n") }}
{% endfor %}
"""
)


def build_index_doc(configs: list[ExampleDocBuildConfig]) -> bytes:
    sorted_configs = sorted(configs, key=lambda c: c.menu_weight)
    return INDEX_TEMPLATE.render({"examples": sorted_configs}).encode("utf-8")


@dataclasses.dataclass
class ExampleDocBuildConfig:
    title: str
    short_description: str
    example_dir: str
    readme_is_index: bool
    append_source_blocks: bool
    menu_weight: int


def load_config(filename: str) -> ExampleDocBuildConfig:
    with open(filename, "rb") as fp:
        raw_config_data = yaml.load(fp, Loader=yaml.Loader)

    title: str = _require_yaml_type(filename, raw_config_data, "title", str)
    short_description: str = _require_yaml_type(
        filename, raw_config_data, "short_description", str
    )

    example_dir: str = _require_yaml_type(filename, raw_config_data, "example_dir", str)
    readme_is_index: bool = _require_yaml_type(
        filename, raw_config_data, "readme_is_index", bool
    )
    append_source_blocks: bool = _require_yaml_type(
        filename, raw_config_data, "append_source_blocks", bool
    )
    menu_weight: bool = _require_yaml_type(
        filename, raw_config_data, "menu_weight", int
    )

    return ExampleDocBuildConfig(
        title=title,
        short_description=short_description,
        example_dir=example_dir,
        readme_is_index=readme_is_index,
        append_source_blocks=append_source_blocks,
        menu_weight=menu_weight,
    )


T = t.TypeVar("T")


def _require_yaml_type(filename: str, data: t.Any, key: str, typ: type[T]) -> T:
    if not isinstance(data, dict):
        _abort("cannot fetch yaml data, non-dict config?")
    value = data.get(key)
    if not isinstance(value, typ):
        _abort(f"{filename}::$.{key} must be of type '{typ.__name__}'")
    return value


def _abort(message: str):
    click.echo(message, err=True)
    raise click.Abort()


if __name__ == "__main__":
    main()
