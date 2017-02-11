# How to install a new version of guiderActor

- If you are developing a new feature on a branch (highly recommended), merge it into trunk.
- Tag the trunk with your new feature.
- ssh to sdss4-hub and check out the new product using `svn export`. You may need to change your group to `sdss4` (`newgrp - sdss4`).
- `svn up` the trunk at APO. It should now contain your merge.
- Run `setup -v guiderActor trunk` to setup the trunk of the product.
- Expand the UPS table of the new tag by doing `eups expandtable ~sdss4/products/LINUX64/guiderActor/<new_tag_version>/ups/idlmapper.table`. Check the results and, if correct, replace the contents of `ups/guiderActor.table` with the output text.
- Declare the new tag as current: `eups declare -c guiderActor <new_tag_version>`
- Double check by running `eups list guiderActor`.
- guiderActor needs to be compiled in a specific way for it to work.
 - Setup the new version with `setup -v guiderActor <new_tag_version>`.
 - cd to the new tag directory `cd $GUIDERACTOR_DIR` and build the product by running `python setup.py build`. That will create a `build/` directory containing `build/lib.linux-x86_64-2.7/` (the Python version and architecture could potentially change).
 - Still at the root directory of the new tag, create a symbolic link to the lib build `ln -s build/lib.linux-x86_64-2.7 lib`.
 - Restart the actor.
