# XSS Research

This is the companion code to "The Power of Guardrails: How to slash your risk of XSS in half."

## Usage

You'll need `poetry` for installing dependencies.

### Summary Notebook

Download the database from http://s3.us-west-2.amazonaws.com/web-assets.r2c.dev/presentations/lvbsides-xss-power-guardrails-v2.db. This is a large file, so it may take a while!

In the 'notebooks/' directory, install the dependencies using `poetry`. Then drop into a shell and launch the Jupyter Notebook.

```
> poetry install
> poetry shell
> jupyter notebook
```

Point the notebook at the database you downloaded and run all the cells. Hopefully it's that easy :-D

### Triage Server

Should be the same process: in `server/`, use poetry to install dependencies and then launch the server:

```
> poetry install
> poetry shell
> python3 xss_research/app.py
```

## Issues

Email grayson@r2c.dev or file an issue on this repo!
