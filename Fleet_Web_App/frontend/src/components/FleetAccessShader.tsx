import { useEffect, useRef } from 'react'

const vertexSource = `attribute vec2 position; void main(){gl_Position=vec4(position,0.0,1.0);}`
const fragmentSource = `
precision mediump float; uniform vec2 resolution; uniform float time;
float line(float v,float w){return smoothstep(w,0.0,abs(v));}
void main(){
 vec2 uv=gl_FragCoord.xy/resolution.xy;
 vec2 p=(gl_FragCoord.xy*2.0-resolution.xy)/min(resolution.x,resolution.y);
 float grid=line(fract(p.x*4.0)-0.5,0.016)+line(fract(p.y*4.0)-0.5,0.016);
 float routeA=line(p.y-sin(p.x*1.8+time*0.22)*0.19+0.13,0.014);
 float routeB=line(p.y+p.x*0.34-0.44,0.010);
 float pulse=0.025/max(length(p-vec2(sin(time*0.28)*0.62,sin(time*0.42)*0.16)),0.025);
 vec3 color=mix(vec3(0.025,0.045,0.075),vec3(0.04,0.08,0.13),uv.y);
 color+=grid*vec3(0.025,0.11,0.16)+routeA*vec3(0.05,0.45,0.95)+routeB*vec3(0.05,0.68,0.48)+pulse*vec3(0.10,0.42,0.92);
 float vignette=smoothstep(1.25,0.25,length(p*vec2(0.72,0.88)));
 gl_FragColor=vec4(color*(0.58+vignette*0.62),1.0);
}`

export function FleetAccessShader() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    const gl = canvas.getContext('webgl', { antialias: false, alpha: false })
    if (!gl) return
    const compile = (type: number, source: string) => {
      const shader = gl.createShader(type)
      if (!shader) return null
      gl.shaderSource(shader, source); gl.compileShader(shader)
      return gl.getShaderParameter(shader, gl.COMPILE_STATUS) ? shader : null
    }
    const vertex = compile(gl.VERTEX_SHADER, vertexSource)
    const fragment = compile(gl.FRAGMENT_SHADER, fragmentSource)
    const program = gl.createProgram()
    if (!vertex || !fragment || !program) return
    gl.attachShader(program, vertex); gl.attachShader(program, fragment); gl.linkProgram(program); gl.useProgram(program)
    const buffer = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, buffer)
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW)
    const position = gl.getAttribLocation(program, 'position'); gl.enableVertexAttribArray(position); gl.vertexAttribPointer(position, 2, gl.FLOAT, false, 0, 0)
    const resolution = gl.getUniformLocation(program, 'resolution'); const time = gl.getUniformLocation(program, 'time')
    let frame = 0
    const render = (now: number) => {
      const ratio = Math.min(window.devicePixelRatio, 1.5); const width = Math.floor(canvas.clientWidth * ratio); const height = Math.floor(canvas.clientHeight * ratio)
      if (canvas.width !== width || canvas.height !== height) { canvas.width = width; canvas.height = height; gl.viewport(0, 0, width, height) }
      gl.uniform2f(resolution, width, height); gl.uniform1f(time, now / 1000); gl.drawArrays(gl.TRIANGLES, 0, 3); frame = requestAnimationFrame(render)
    }
    frame = requestAnimationFrame(render)
    return () => cancelAnimationFrame(frame)
  }, [])
  return <canvas aria-hidden="true" className="absolute inset-0 h-full w-full bg-[#07111f]" ref={canvasRef} />
}
