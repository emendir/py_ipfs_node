#define PY_SSIZE_T_CLEAN
#include <Python.h>

static PyMethodDef DummyMethods[] = {
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef dummymodule = {
    PyModuleDef_HEAD_INIT,
    "_dummy",
    NULL,
    -1,
    DummyMethods
};

PyMODINIT_FUNC
PyInit__dummy(void) {
    return PyModule_Create(&dummymodule);
}