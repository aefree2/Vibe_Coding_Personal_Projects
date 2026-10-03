Welcome to the repository for Vibe Coding at Project Scale: Comparing Vibe-Coded and Human-Written Personal Software Projects

Comment data and codebook is located in /comments

Topic data and codebook is located in /Project_topic

Non-functional code quality metrics are located in /non_functional

Language data is located in /non_functional/viz_notebooks/lang_viz.ipynb and in /non_functional/file_level.csv

Low-level metrics can be found in /dataset_features

Due to the large size, most of the data files have been zipped. Please unzip prior to running. 

If you would like to run the repository (not necessary):

Please run

make_experiment.sh

Once this has completed (may take >= 8 hours), 

python3 mixed_effects_file.py

python3 mixed_effects_proj.py

python3 mixed_effects_class.py

python3 mixed_effects_fn.py

python3 mixed_effects_file_py.py

python3 mixed_effects_proj_py.py
