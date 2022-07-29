# Certificates of quantum many-body properties assisted by machine learning 
> Repository hosting the code of the work '<a href='https://arxiv.org/abs/2103.03830'>Certificates of quantum many-body properties assisted by machine learning</a>' authored by Borja Requena, Gorka Muñoz-Gil, Maciej Lewenstein, Vedran Dunjko and Jordi tura. 


In this repository you can find the source code and a set of notebooks providing a thorough example of how to use the library and how to reproduce the figures shown in the paper. 

- The source code can be found in two directories: it is within `bounce` and in `nbs` (see the [docs](https://borjarequena.github.io/BOUNCE/)). Bounce stands for BOUNd CErtification. This project is based on [nbdev](https://github.com/fastai/nbdev), which generates the library from notebooks. These contain complementary explanations of the code with small examples. 
- The `examples` directory contains a set of notebooks that conform a tutorial of how to use this library, with extended explanations and examples. The examples contain the source code to reproduce the figures from the paper, which can be plotted in the `04_plots.ipynb`.

## Install

In order to use the library, you will have to clone this repository with `git clone https://github.com/BorjaRequena/BOUNCE.git` and install it via `pip install BOUNCE`. In order to edit the source code and adapt it to your particular problems, you may install it in editable form with `pip install -e BOUNCE`.
{% include note.html content='to perform the installation, you must be in the immediately higher level along the path of the cloned repository. For instance, if the repository is in the directory `~/what/ever/BOUNCE`, go to `~/what/ever/` directory to run the `pip install -e BOUNCE` command.  ' %}
