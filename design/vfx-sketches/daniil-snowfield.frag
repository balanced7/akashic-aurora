#version 300 es
precision highp float;
out vec4 outColor;
uniform vec2  u_res;
uniform float u_time;

// ingested: daniil-snowfield
#define iTime (u_time)
#define iResolution vec3(u_res, 1.0)
#define iMouse vec4(0.0)
#define iTimeDelta (1.0 / 60.0)
#define iFrameRate (60.0)
#define iFrame (int(u_time * 60.0))
#define iSampleRate (44100.0)
#define iDate vec4(2026.0, 1.0, 1.0, u_time)

// Daniil's find #1: ray-marched northern lights over snow before dawn.
// FAITHFUL PORT, not verbatim -- the original needs four texture channels the bench
// does not stock, so exactly five substitutions were made, each named:
//   1. noise(vec3): textureLod(iChannel2) LUT  -> computed value noise (hash-based)
//   2. getHeight(): texture(iChannel3/2) snow  -> procedural 2D value-noise fbm
//   3. camera: texelFetch(iChannel0) buffer    -> fixed targetDir (0, 0.12, -1)
//   4. dither: blue-noise texture (iChannel1)  -> golden-ratio hash jitter
//   5. iChannelResolution guard                -> removed (no channels exist)
// Everything else -- the AABB march, density shaping, sky, shading, mountains,
// ACES -- is the author's, untouched. Its very first comment asks "is there a fast
// LUT-free 3D gradient noise approach?" -- substitution 1 is that question, answered
// under duress.

#define PI 3.14159
#define TWO_PI 2.0*PI

const float STEPS = 32.0;
const float auroraSpeed = 0.5;
const float strengthMultiplier = 0.015;
const vec3 baseColour = vec3(0.35, 1, 0.01);
const vec3 highColour = vec3(0.5, 0.0, 0.2);

const float auroraStart = 50.0;
const float aabbHeight = 75.0;
const vec3 minCorner = vec3(-250.0, auroraStart, -500.0);
const vec3 maxCorner = vec3(250.0, auroraStart + aabbHeight, 500.0);

const float flickerSpeed = 5.0;

float sunLocation = 0.5;
float sunHeight = -3.9;

const vec3 skyColour = vec3(0.45, 0.7, 1.0);
const vec3 distantColour = 0.04 * skyColour;

#define DITHERING
const float goldenRatio = 1.61803398875;

vec3 rayDirection(float fieldOfView, vec2 fragCoord) {
    vec2 xy = fragCoord - iResolution.xy / 2.0;
    float z = (0.5 * iResolution.y) / tan(radians(fieldOfView) / 2.0);
    return normalize(vec3(xy, -z));
}

mat3 lookAt(vec3 camera, vec3 targetDir, vec3 up){
  vec3 zaxis = normalize(targetDir);
  vec3 xaxis = normalize(cross(zaxis, up));
  vec3 yaxis = cross(xaxis, zaxis);
  return mat3(xaxis, yaxis, -zaxis);
}

float getGlow(float dist, float radius, float intensity){
    dist = max(dist, 1e-7);
    return pow(radius/dist, intensity);
}

// ---- substitution 1: LUT-free 3D value noise (replaces the iChannel2 fetch) ----
float hash13(vec3 p3){
    p3 = fract(p3 * 0.1031);
    p3 += dot(p3, p3.zyx + 31.32);
    return fract((p3.x + p3.y) * p3.z);
}
float noise( in vec3 x ){
    vec3 i = floor(x);
    vec3 f = fract(x);
    f = f*f*(3.0-2.0*f);
    float n000=hash13(i), n100=hash13(i+vec3(1,0,0));
    float n010=hash13(i+vec3(0,1,0)), n110=hash13(i+vec3(1,1,0));
    float n001=hash13(i+vec3(0,0,1)), n101=hash13(i+vec3(1,0,1));
    float n011=hash13(i+vec3(0,1,1)), n111=hash13(i+vec3(1,1,1));
    float nx00=mix(n000,n100,f.x), nx10=mix(n010,n110,f.x);
    float nx01=mix(n001,n101,f.x), nx11=mix(n011,n111,f.x);
    return mix(mix(nx00,nx10,f.y), mix(nx01,nx11,f.y), f.z);
}

float fbm3D(vec3 pos, int limit){
    float sum = 0.0;
    float weightSum = 0.0;
    float weight = 1.0;
    float frequency = 1.0;
    for(int oct = 0; oct < 3; oct++){
        vec3 p = pos * frequency;
        float val = noise(p * frequency);
        sum += (1.0-abs(val)) * weight;
        weightSum += weight;
        weight *= 0.5;
        frequency *= 2.0;
    }
    float n = sum / weightSum;
    return clamp(n, 0.0, 1.0);
}

#define HASHSCALE 0.1031
float hash(float p){
    vec3 p3  = fract(vec3(p) * HASHSCALE);
    p3 += dot(p3, p3.yzx + 19.19);
    return fract((p3.x + p3.y) * p3.z);
}
float fade(float t) { return t*t*t*(t*(6.*t-15.)+10.); }
float grad(float hash, float p){
    int i = int(1e4*hash);
    return (i & 1) == 0 ? p : -p;
}
float perlinNoise1D(float p){
    float pi = floor(p), pf = p - pi, w = fade(pf);
    return mix(grad(hash(pi), pf), grad(hash(pi + 1.0), pf - 1.0), w) * 2.0;
}
float fbm(float pos, int octaves, float persistence){
    float total = 0.0, frequency = 1.0, amplitude = 1.0, maxValue = 0.0;
    for(int i = 0; i < octaves; ++i){
        total += perlinNoise1D(pos * frequency) * amplitude;
        maxValue += amplitude;
        amplitude *= persistence;
        frequency *= 2.0;
    }
    return total / maxValue;
}

vec2 intersectAABB(vec3 rayOrigin, vec3 rayDir, vec3 boxMin, vec3 boxMax) {
    vec3 tMin = (boxMin - rayOrigin) / rayDir;
    vec3 tMax = (boxMax - rayOrigin) / rayDir;
    vec3 t1 = min(tMin, tMax);
    vec3 t2 = max(tMin, tMax);
    float tNear = max(max(t1.x, t1.y), t1.z);
    float tFar = min(min(t2.x, t2.y), t2.z);
    return vec2(tNear, tFar);
}

bool insideAABB(vec3 p){
    float eps = 1e-4;
    return  (p.x > minCorner.x-eps) && (p.y > minCorner.y-eps) && (p.z > minCorner.z-eps) &&
            (p.x < maxCorner.x+eps) && (p.y < maxCorner.y+eps) && (p.z < maxCorner.z+eps);
}

bool getAABBIntersection(vec3 org, vec3 dir, out float distToStart, out float totalDistance){
    vec2 intersections = intersectAABB(org, dir, minCorner, maxCorner);
    if(insideAABB(org)){
        intersections.x = 1e-4;
    }
    distToStart = intersections.x;
    totalDistance = intersections.y - intersections.x;
    return intersections.x > 0.0 && (intersections.x < intersections.y);
}

vec3 auroraColour(float h){
    return mix(baseColour, highColour, h);
}

vec3 getAuroraPosition(vec3 position, float speed){
    float h = (position.y-auroraStart)/aabbHeight;
    vec3 pos = 0.042*vec3(position.x, 2.0*speed, 0.225*position.z+speed*0.5);
    pos.x += 0.3*h + 5.5*cos(0.005*position.z);
    pos.x += 0.02*perlinNoise1D(0.1*position.z+speed*2.0);
    return pos;
}

float getAuroraDensity(vec3 position){
    float speed = iTime * auroraSpeed;
    vec3 pos = getAuroraPosition(position, speed);
    float n = fbm3D(pos, 3);
    vec3 p = vec3(n, position.y-minCorner.y, n);
    vec3 a = p * vec3(1.0, 0.006, 1.0);
    a.y += 0.48;
    a.y += 0.015*perlinNoise1D(1.0*speed + pos.z);
    a.y += 0.015*perlinNoise1D(-2.0*speed + pos.z);
    float density = getGlow(length(a), 0.7, 10.0);
    density *= cos(0.13*pos.x);
    return max(0.0, density);
}

vec3 getAuroraColour(vec3 org, vec3 dir, float offset){
    vec3 colour = vec3(0);
    float density = 0.0;
    float distToStart = 0.0;
    float totalDistance = 0.0;
    bool renderAurora = getAABBIntersection(org, dir, distToStart, totalDistance);
    if(!renderAurora){
        return colour;
    }
    float stepSize = totalDistance / float(STEPS);
    distToStart += stepSize * offset;
    vec3 p = org + distToStart * dir;
    float dist = distToStart;
    vec3 col = vec3(0);
    for(float i = 0.0; i < STEPS; i++){
        density = getAuroraDensity(p);
        col += density * auroraColour((p.y-minCorner.y)/(maxCorner.y-minCorner.y));
        dist += stepSize;
        p = org + dir * dist;
    }
    return strengthMultiplier * col * stepSize;
}

vec3 rand33(vec3 p3){
    p3 = fract(p3 * vec3(.1031, .1030, .0973));
    p3 += dot(p3, p3.yxz+33.33);
    return fract((p3.xxy + p3.yxx)*p3.zyx);
}

float getStars(vec3 rayDir){
    float scale = 112.0;
    vec3 id = floor(rayDir * scale);
    float d = length(scale * rayDir - (id + 0.5));
    float stars = 0.0;
    vec3 rnd = rand33(id);
    if(rnd.x > 0.92 && d < 0.15){
        stars = getGlow(d, 0.075, 2.5 - 2.0 * sin(rnd.y * flickerSpeed * iTime));
    }
    return stars;
}

vec3 getSkyColour(vec3 rayDir){
    vec3 sunDirection = normalize(vec3(cos(sunLocation), sunHeight, sin(sunLocation)));
    float halo = dot(rayDir, sunDirection);
    float mu = 0.5+0.5*halo;
    vec3 sunColour = vec3(1.0, 0.25, 0.01);
    vec3 sun = 0.15 * sunColour * getGlow(max(1.0-mu, 0.1), 0.39, 10.0);
    vec3 blue = mix(vec3(1), skyColour, smoothstep(1.0, -0.5, halo));
    blue = mix(blue, vec3(0), smoothstep(1.0, -0.75, halo));
    vec3 stars = vec3(getStars(rayDir));
    stars = mix(stars, blue, mu);
    vec3 planetDirection = -normalize(vec3(1,1,0));
    float planet = 0.5+0.5*dot(rayDir, planetDirection);
    stars += 0.1*getGlow(planet, 5e-6, 0.95);
    planetDirection = -normalize(vec3(0.3, 0.25, 1.0));
    planet = 0.5+0.5*dot(rayDir, planetDirection);
    stars += 0.1*getGlow(planet, 5e-6, 0.95);
    return mix(0.5*stars, sun, mu)
        + 0.04*mix(vec3(1.0,0.5,0.3), 0.5*skyColour, smoothstep(0.4, 0.57, 0.5+0.5*rayDir.y));
}

vec3 shading(vec3 org, vec3 position, vec3 normal, vec3 rayDir){
    vec3 auroraCol = 0.75*baseColour;
    vec3 specularColour = vec3(1);
    float ambientStrength = 0.1;
    float specularStrength = 0.005;
    float shininess = 1.0;
    vec3 ambientColour = vec3(0.1);
    vec3 diffuseColour = vec3(1.15);
    vec3 lightPos = vec3(-120.0*cos(0.005*position.z), auroraStart, position.z);
    vec3 lightDirection = normalize(lightPos-position);
    if(length(lightPos - org) > 1500.0){
        auroraCol = vec3(0);
    }
    vec3 halfwayDir = normalize(lightDirection - rayDir);
    float spec = pow(max(dot(normal, halfwayDir), 0.0), shininess);
    vec3 specular = spec * specularColour * auroraCol;
    float aurora = max(dot(normal, lightDirection), 0.0);
    vec3 auroraLight = aurora * auroraCol;
    float sky = max(dot(normal, vec3(0,1,0)), 0.0);
    vec3 skyLight = sky * skyColour;
    vec3 result = vec3(0.0);
    result += 0.03 * auroraLight;
    result += 0.035 * skyLight;
    result *= diffuseColour;
    result += ambientStrength * ambientColour + specularStrength * specular;
    float fadeD = clamp(length(position-org)/900.0, 0.0, 1.0);
    return  mix(result, distantColour, smoothstep(0.35, 1.0, fadeD));
}

// ---- substitution 2: procedural snow height (replaces iChannel3/iChannel2 fetches) ----
float vnoise2(vec2 co){
    vec2 i=floor(co), f=fract(co);
    f=f*f*(3.0-2.0*f);
    float a=hash13(vec3(i,7.0)), b=hash13(vec3(i+vec2(1,0),7.0));
    float c=hash13(vec3(i+vec2(0,1),7.0)), d=hash13(vec3(i+vec2(1,1),7.0));
    return mix(mix(a,b,f.x), mix(c,d,f.x), f.y);
}
float getHeight(vec3 p){
    vec2 q = 0.004*p.xz;
    float drift = 0.6*vnoise2(q*6.0) + 0.3*vnoise2(q*13.0) + 0.1*vnoise2(q*29.0);
    return 2.5 * drift + 0.002 * vnoise2(0.25*p.xz);
}

vec3 getNormal(vec3 p, float t){
    float eps = 0.001 * t;
    return normalize(vec3(
            getHeight(vec3(p.x-eps, p.y, p.z))
            - getHeight(vec3(p.x+eps, p.y, p.z)),
            2.0*eps,
            getHeight(vec3(p.x, p.y, p.z-eps))
            - getHeight(vec3(p.x, p.y, p.z+eps))
        ));
}

bool getPlaneIntersection(vec3 org, vec3 ray, vec3 planePoint, vec3 normal, out float t){
    float denom = dot(normal, ray);
    if (denom > 1e-6) {
        vec3 p0l0 = planePoint - org;
        t = dot(p0l0, normal) / denom;
        return (t >= 0.0);
    }
    return false;
}

vec3 getGround(vec3 org, vec3 rayDir, float t){
    vec3 p = org + t * rayDir;
    vec3 normal = getNormal(p, t);
    return shading(org, p, normal, rayDir);
}

vec3 getMountains(vec3 rayDir, vec3 sky){
    float phi = atan(rayDir.x, rayDir.z);
    float offset = -0.06*(0.5+0.5*sin(6.0*phi));
    float detail = 0.045*fbm(phi, 6, 0.55);
    float limit = PI*0.99;
    float span = PI - limit;
    if(phi > limit || phi < -limit){
        detail *= -(sign(phi)*phi - PI)/span;
    }
    detail += 0.005;
    offset += detail;
    return mix(distantColour, sky, smoothstep(0.0, 0.003, rayDir.y+offset));
}

vec3 ACESFilm(vec3 x){
    return clamp((x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14), 0.0, 1.0);
}

void mainImage( out vec4 fragColor, in vec2 fragCoord ){
    vec3 rayDir = rayDirection(60.0, fragCoord);
    vec3 cameraPos = vec3(0,10,0);
    // ---- substitution 3: fixed camera target (replaces the iChannel0 buffer read) ----
    vec3 targetDir = vec3(0.0, 0.12, -1.0);
    vec3 up = vec3(0.0, 1.0, 0.0);
    mat3 viewMatrix = lookAt(cameraPos, targetDir, up);
    rayDir = normalize(viewMatrix * rayDir);

    // ---- substitution 4: golden-ratio hash dither (replaces blue-noise iChannel1) ----
    float offset = 0.0;
    #ifdef DITHERING
    offset = fract(hash13(vec3(fragCoord, 1.0)) + fract(iTime) * goldenRatio);
    #endif

    vec3 colour = getAuroraColour(cameraPos + rayDir * 10.0, rayDir, offset);

    vec3 background = vec3(0.0);
    if(rayDir.y > 0.0){
        background = getSkyColour(rayDir);
        background = getMountains(rayDir, background);
    }

    float t = 0.0;
    if(getPlaneIntersection(cameraPos, rayDir, vec3(0), vec3(0,-1,0), t)){
        background = getGround(cameraPos, rayDir, t);
    }

    colour += background;
    colour = ACESFilm(colour);
    colour = pow(colour, vec3(0.4545));
    fragColor = vec4(colour, 1.0);
}

void main(){ mainImage(outColor, gl_FragCoord.xy); }
