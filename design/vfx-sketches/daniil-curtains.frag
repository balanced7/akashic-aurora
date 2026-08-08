#version 300 es
precision highp float;
out vec4 outColor;
uniform vec2  u_res;
uniform float u_time;

// ingested: daniil-curtains
#define iTime (u_time)
#define iResolution vec3(u_res, 1.0)
#define iMouse vec4(0.0)
#define iTimeDelta (1.0 / 60.0)
#define iFrameRate (60.0)
#define iFrame (int(u_time * 60.0))
#define iSampleRate (44100.0)
#define iDate vec4(2026.0, 1.0, 1.0, u_time)

// Daniil's find #2, verbatim: domain-warped fbm aurora curtains + perlin ridge.
// Rendered as reference before the confluence borrows its curtain engine.
float hash(vec2 co) { return fract(sin(dot(co, vec2(12.9898, 78.233))) * 43758.5453); }
float hash(float x, float y) { return hash(vec2(x, y)); }

float shash(vec2 co)
{
	float x = co.x;
	float y = co.y;

	float corners = (hash(x-1., y-1.) + hash(x+1., y-1.) + hash(x-1., y+1.) + hash(x+1., y+1.))/16.;
	float sides   = (hash(x-1., y) + hash(x+1., y) + hash(x, y-1.) + hash(x, y+1.))/8.;
	float center  = hash(co) / 4.;

	return corners + sides + center;
}

float noise(vec2 co)
{
	vec2 pos  = floor(co);
	vec2 fpos = co - pos;

	fpos = (3.0 - 2.0*fpos)*fpos*fpos;

	float c1 = shash(pos);
	float c2 = shash(pos + vec2(0.0, 1.0));
	float c3 = shash(pos + vec2(1.0, 0.0));
	float c4 = shash(pos + vec2(1.0, 1.0));

	float s1 = mix(c1, c3, fpos.x);
	float s2 = mix(c2, c4, fpos.x);

	return mix(s1, s2, fpos.y);
}

float pnoise(vec2 co, int oct)
{
	float total = 0.0;
	float m = 0.0;

	for(int i=0; i<oct; i++)
	{
		float freq = pow(2.0, float(i));
		float amp  = pow(0.5, float(i));

		total += noise(freq * co) * amp;
		m += amp;
	}

	return total/m;
}


// FBM: repeatedly apply Perlin noise to position
vec2 fbm(vec2 p, int oct)
{
	return vec2(pnoise(p + vec2(iTime, 0.0), oct), pnoise(p + vec2(-iTime, 0.0), oct));
}

float fbm2(vec2 p, int oct)
{
	return pnoise(p + 10.*fbm(p, oct) + vec2(0.0, iTime), oct);
}

// Calculate the lights themselves
vec3 lights(vec2 co)
{
	float d,r,g,b,h;
	vec3 rc,gc,bc,hc;

	// Red (top)
	r = fbm2(co * vec2(1.0, 0.5), 1);
	d = pnoise(2.*co+vec2(0.3*iTime), 1);
	rc = vec3(1, 0.0, 0.0) * r * smoothstep(0.0, 2.5+d*r, co.y) * smoothstep(-5., 1., 5.-co.y-2.*d);

	// Green (middle)
	g = fbm2(co * vec2(2., 0.5), 4);
	gc = 0.8*vec3(0.5,1.0,0.0) * clamp(2.*pow((3.-2.*g)*g*g,2.5)-0.5*co.y, 0.0, 1.0) * smoothstep(-2.*d, 0.0, co.y) * smoothstep(0.0, 0.3, 1.1+d-co.y);

	g = fbm2(co * vec2(1.0, 0.2), 2);
	gc += 0.5*vec3(0.5,1.0,0.0) * clamp(2.*pow((3.-2.*g)*g*g,2.5)-0.5*co.y, 0.0, 1.0) * smoothstep(-2.*d, 0.0, co.y) * smoothstep(0.0, 0.3, 1.1+d-co.y);


	// Blue (bottom)
	h = pnoise(vec2(5.0*co.x, 5.0*iTime), 1);
	hc = vec3(0.0, 0.8, 1.0) * pow(h+0.1,2.0) * smoothstep(-2.*d, 0.0, co.y+0.2) * smoothstep(-h, 0.0, -co.y-0.4);

	return rc+gc+hc;
}

// Simple Perlin mountains (yes, they change over time :D)
vec3 landscape(vec2 co)
{
	float n = pnoise(vec2(20.0*co.x, 0.1*iTime), 2);

	if (co.y < n*0.2+0.1)
		return vec3(0.0);

    vec3 col = vec3(0.5*pow(co.y-1.,2.));

    vec2 sco = co*500.0;
	if (hash(floor(sco)) < 0.005)
    {
        float s1 = hash(floor(sco)*floor(sco));
        float s2 = max(1.-2.*distance(vec2(0.5),fract(sco)), 0.0);
		return col + vec3(s1*s2);
    }

	return col;
}

// The main image!
void mainImage( out vec4 fragColor, in vec2 fragCoord )
{
	vec2 uv = fragCoord.xy / iResolution.xy;
	vec2 co = fragCoord.xy/float(iResolution.y);

    vec3 col = vec3(0.0);

	// Landscape
	col += landscape(co);

	// Aurora (with some transformation)
    float s = 0.1*sin(iTime);
    float f = 0.3+0.4*pnoise(vec2(5.*uv.x, 0.3*iTime),1);
	vec2 aco = co;
	aco.y -= f;
	aco *= 10.*uv.x+5.0;
	col += 0.5*lights(aco)
           * (smoothstep(0.3, 0.6, pnoise(vec2(10.*uv.x, 0.3*iTime),1))
           +  0.5*smoothstep(0.5, 0.7, pnoise(vec2(10.*uv.x,iTime),1)));

	fragColor = vec4(col, 1.0);
}

void main(){ mainImage(outColor, gl_FragCoord.xy); }
