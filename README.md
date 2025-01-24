# AnchorPy
<div align="center">
    <img src="https://raw.githubusercontent.com/kevinheavey/anchorpy/main/docs/img/logo.png" width="40%" height="40%">
</div>

---

[![Discord Chat](https://img.shields.io/discord/889577356681945098?color=blueviolet)](https://discord.gg/sxy4zxBckh)  

AnchorPy is the gateway to interacting with [Anchor](https://github.com/project-serum/anchor) programs in Python.
It provides:

- A static client generator
- A dynamic client similar to `anchor-ts`
- A Pytest plugin
- A CLI with various utilities for Anchor Python development.

Read the [Documentation](https://kevinheavey.github.io/anchorpy/).



## Installation (requires Python >=3.9)

```sh
pip install anchorpy[cli, pytest]

```
Or, if you're not using the CLI or Pytest plugin features of AnchorPy you can just run `pip install anchorpy`.


### Development Setup

AnchorPy does not currently support Solana 2.0 or Anchor 0.30.0.

If you want to contribute to AnchorPy, you will require the following installed, in the following order:

- [poetry](https://python-poetry.org/docs/#installation)

- [Rust](https://rustup.rs/)

- [Solana CLI](https://solana.com/docs/intro/installation) for Solana 1.18.26

- [Anchor CLI](https://www.anchor-lang.com/docs/installation) for Anchor version 0.29.0

Now, follow these steps to get set up:

1. Generate a new Solana keypair for local development and configure the Solana CLI to use a localnet for testing:

```sh
solana-keygen new --outfile ~/.config/solana/id.json
solana config set --url localhost

```

2. Git clone the repo and initialise the submodules:
```sh
git clone https://github.com/kevinheavey/anchorpy.git
git submodule update --init

```

3. Install dev dependencies:
```sh
poetry install

```

4. Run the included tests:
```sh
poetry run pytest

```
