#!/usr/bin/env -S pipx run

# /// script
# requires-python = ">=3.9"
# dependencies = ["click", "jinja2", "pyyaml"]
# ///

from __future__ import annotations

import base64
import dataclasses
import glob
import gzip
import io
import json
import os
import pathlib
import tarfile
import textwrap
import typing as t
import urllib.parse

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

HERE = pathlib.Path(__file__).parent
REPO_ROOT = HERE.parent


@click.option(
    "-o",
    "--output",
    default="doc_bundle.tar.gz",
    type=click.Path(
        writable=True, dir_okay=False, resolve_path=True, path_type=pathlib.Path
    ),
    help="Output filename.",
)
@click.command
def main(output: pathlib.Path) -> None:
    click.echo("Bundling examples for docs.globus.org", err=True)
    os.chdir(REPO_ROOT)

    with tarfile.open(output, "w:gz") as archive:
        for filename, file_bytes in build_all_files():
            file_info = tarfile.TarInfo(filename)
            file_info.size = len(file_bytes)
            archive.addfile(file_info, io.BytesIO(file_bytes))

    click.echo(f"Done. Output is available at {output}")


def build_all_files() -> t.Iterator[tuple[str, bytes]]:
    all_example_configs: list[ExampleDocBuildConfig] = []
    for config_file in find_build_configs():
        source_dir = config_file.parent
        click.echo(f"building for {source_dir}", err=True)

        config = load_config(config_file)
        all_example_configs.append(config)

        for sub_path in config.include_files:
            with open(source_dir / sub_path, "rb") as fp:
                yield f"{config.example_dir}/{sub_path}", fp.read()

        yield f"{config.example_dir}/index.adoc", render_example_index_doc(
            source_dir, config
        )
    yield "index.adoc", build_index_doc(all_example_configs)


def find_build_configs() -> t.Iterator[pathlib.Path]:
    for item in glob.glob("*/**/.doc_config.yaml", recursive=True):
        yield pathlib.Path(item)


def build_ide_link(source_dir: pathlib.Path) -> str:
    definition = _encode_link_part(source_dir / "definition.json")
    input_schema = _encode_link_part(source_dir / "input_schema.json")
    return (
        "https://globus.github.io/flows-ide?format=gzip&"
        f"d={definition}&s={input_schema}"
    )


def _encode_link_part(source_path: pathlib.Path) -> str:
    # load and dump JSON to strip whitespace
    loaded_doc = json.loads(source_path.read_bytes())
    doc_bytes = json.dumps(loaded_doc, separators=(",", ":")).encode("utf-8")
    gzipped_doc = gzip.compress(doc_bytes)
    b64_gzipped_doc = base64.b64encode(gzipped_doc)
    return urllib.parse.quote_from_bytes(b64_gzipped_doc.rstrip(b"="))


def render_example_index_doc(
    source_dir: pathlib.Path, config: ExampleDocBuildConfig
) -> bytes:
    content: bytes
    if config.index_source.mode == "copy":
        if len(config.index_source.filenames) != 1:
            raise ValueError("A 'copy' config cannot have multiple filenames.")
        content = (source_dir / config.index_source.filenames[0]).read_bytes()
    elif config.index_source.mode == "concat":
        content = b"".join(
            (source_dir / filename).read_bytes()
            for filename in config.index_source.filenames
        )
    else:
        raise NotImplementedError(
            f"Unsupported index_source mode: {config.index_source.mode}"
        )

    if config.append_source_blocks:
        content = append_source_blocks(content)

    ide_link: str | None = None
    if config.include_ide_link:
        ide_link = build_ide_link(source_dir)

    content = prepend_preamble(config, ide_link, content)
    return content


def prepend_preamble(
    config: ExampleDocBuildConfig, ide_link: str | None, content: bytes
) -> bytes:
    preamble = textwrap.dedent(
        f"""\
        ---
        menu_weight: {config.menu_weight}
        ---

        """
    )

    if ide_link is not None:
        preamble += textwrap.dedent(
            f"""
            :flows_ide_link: {ide_link}

            """
        )

    return preamble.encode("utf-8") + content


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
{{ item.short_description | replace("\n\n", "\n+\n") }}
{% endfor %}
"""
)


def build_index_doc(configs: list[ExampleDocBuildConfig]) -> bytes:
    sorted_configs = sorted(configs, key=lambda c: c.menu_weight)
    return INDEX_TEMPLATE.render({"examples": sorted_configs}).encode("utf-8")


def load_config(config_file: pathlib.Path) -> ExampleDocBuildConfig:
    with open(config_file, "rb") as fp:
        raw_config_data = yaml.safe_load(fp)

    if not isinstance(raw_config_data, dict):
        _abort(f"cannot fetch yaml data from {config_file}, non-dict config?")

    return ExampleDocBuildConfig._load(raw_config_data)


@dataclasses.dataclass
class ExampleDocBuildConfig:
    title: str
    short_description: str
    example_dir: str
    index_source: IndexSourceConfig
    append_source_blocks: bool
    menu_weight: int
    include_ide_link: bool
    include_files: list[str]

    @classmethod
    def _load(cls, data: dict[str, t.Any]) -> t.Self:

        return cls(
            title=data["title"],
            short_description=data["short_description"],
            example_dir=data["example_dir"],
            index_source=IndexSourceConfig._load(data["index_source"]),
            append_source_blocks=data["append_source_blocks"],
            menu_weight=data["menu_weight"],
            include_ide_link=data.get("include_ide_link", True),
            # fill the default files to include if not present
            include_files=data.get(
                "include_files",
                ["definition.json", "input_schema.json", "sample_input.json"],
            ),
        )


@dataclasses.dataclass
class IndexSourceConfig:
    mode: t.Literal["copy", "concat"]
    filenames: list[str]

    @classmethod
    def _load(cls, data: dict[str, t.Any]) -> t.Self:
        if "copy" in data:
            return cls(mode="copy", filenames=[data["copy"]])
        elif "concat" in data:
            return cls(mode="concat", filenames=data["concat"]["files"])
        else:
            _abort("Unexpected error: index_source did not have copy or concat")


def _abort(message: str) -> t.NoReturn:
    click.echo(message, err=True)
    raise click.Abort()


if __name__ == "__main__":
    main()
