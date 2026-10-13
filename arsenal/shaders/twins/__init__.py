"""CPU twins of the house GLSL library (arsenal/web/glsl/): one Python function per GLSL function where the maths allows.

WHY. A shader cannot print. A twin is the same maths on the CPU, written with numpy, so a test can pin a module to
reference values (published test vectors where they exist: a hash paper's table, the sRGB standard's round trip, a tone
curve at fixed points) without a GPU in the loop. Like a bench multimeter beside the oscilloscope: the scope shows the
picture, the meter proves the voltage. Each module's header names its twin ("twin": "arsenal/shaders/twins/<area>.py:fn").

Rules: hashes are bit-exact with uint32 arithmetic; colour and tone agree to 1e-6; names match the GLSL names, so a
grep finds both halves. Apache-2.0, written fresh from the mathematics, like the modules themselves.
"""
