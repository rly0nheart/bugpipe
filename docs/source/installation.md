# Installation

## From PyPI

Bugpipe is available on PyPI as `bugpipe`. Below are instructions on how to install both the library and CLI utility:

```shell
pip install bugpipe
```

## Docker Image

If you prefer running the CLI utility inside a docker container, a `Dockerfile` is provided.

```shell
docker build -t bugpipe-cli .
```

> This assumes your current working directory is `bugpipe/`

## Nix

For Nix users, a `shell.nix` is provided. Once you enter the shell, you will be able to do stuff.

```shell
nix-shell
```
