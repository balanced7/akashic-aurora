//! {"name": "rot2", "kind": "helper", "from": "standard", "note": "In-place 2D rotation. Two multiplies; the workhorse of every domain transform here.", "order": 10}
void pR(inout vec2 p,float a){ p=cos(a)*p+sin(a)*vec2(p.y,-p.x); }
