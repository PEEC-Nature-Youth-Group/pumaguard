# Release Management

To create a new release simply tag a commit on the main branch. Once that tag
is pushed, the [test-and-package.yaml](.github/workflows/test-and-package.yaml)
workflow will create a new release and attach the build artifacts, i.e. the
Python wheel and the snap, to the release.

Our naming convention for tags is to use a simple integer (only the major in
semantic versioning), prepended with the letter `v`, i.e.,

```
v42
```
