# Makefile for trnsystor documentation (Zensical)

.PHONY: help serve build clean

help:
	uv run zensical --help

serve:
	uv run zensical serve

build:
	uv run zensical build

clean:
	rm -rf site/
