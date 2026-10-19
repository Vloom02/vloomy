#!/usr/bin/env node
// Canal "vloomy" para Claude Code (capa 2): Vloomy le pasa tareas pesadas a una sesión de Claude Code
// que corre con tu suscripción, y recibe las respuestas y los pedidos de permiso para decirlos en voz alta.
// Protocolo de canales: https://code.claude.com/docs/en/channels-reference
// Ojo: stdout es el canal MCP; para depurar usar console.error.
import http from 'node:http'
import { readFileSync } from 'node:fs'
import { timingSafeEqual } from 'node:crypto'
import { Server } from '@modelcontextprotocol/sdk/server/index.js'
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js'
import { CallToolRequestSchema, ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js'
import { z } from 'zod'

const PUERTO = Number(process.env.VLOOMY_CANAL_PUERTO ?? 8788)
const token = process.env.VLOOMY_TOKEN ?? leerToken()

function leerToken() {
  const env = readFileSync(new URL('../.env', import.meta.url), 'utf8')
  const m = env.match(/^VLOOMY_TOKEN=(.+)$/m)
  if (!m) throw new Error('falta VLOOMY_TOKEN en .env: arrancá vloomy.cmd una vez y se genera solo')
  return m[1].trim()
}

const oyentes = new Set()
function emitir(evento) {
  const linea = JSON.stringify(evento) + '\n'
  for (const res of oyentes) res.write(linea)
}

const mcp = new Server(
  { name: 'vloomy', version: '0.1.0' },
  {
    capabilities: {
      experimental: { 'claude/channel': {}, 'claude/channel/permission': {} },
      tools: {},
    },
    instructions:
      'Las tareas de Vloomy (el asistente por voz del usuario) llegan como <channel source="vloomy" id="...">. ' +
      'Hacé la tarea y al terminar llamá a la herramienta responder con ese id y un resumen de una o dos frases ' +
      'en español rioplatense, sin markdown: Vloomy lo lee en voz alta.',
  },
)

mcp.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [{
    name: 'responder',
    description: 'Le devuelve a Vloomy el resultado de una tarea para que lo diga en voz alta.',
    inputSchema: {
      type: 'object',
      properties: { id: { type: 'string' }, texto: { type: 'string' } },
      required: ['id', 'texto'],
    },
  }],
}))

mcp.setRequestHandler(CallToolRequestSchema, async req => {
  if (req.params.name !== 'responder') throw new Error(`herramienta desconocida: ${req.params.name}`)
  const { id, texto } = req.params.arguments
  emitir({ tipo: 'respuesta', id: String(id), texto: String(texto) })
  return { content: [{ type: 'text', text: oyentes.size ? 'entregado' : 'Vloomy no está conectado: no se entregó' }] }
})

// Claude Code avisa acá cuando una herramienta necesita aprobación; Vloomy la pregunta por voz.
mcp.setNotificationHandler(
  z.object({
    method: z.literal('notifications/claude/channel/permission_request'),
    params: z.object({
      request_id: z.string(),
      tool_name: z.string(),
      description: z.string(),
      input_preview: z.string(),
    }),
  }),
  async ({ params }) => emitir({ tipo: 'permiso', ...params }),
)

await mcp.connect(new StdioServerTransport())

function autorizado(req) {
  const recibido = Buffer.from(req.headers.authorization ?? '')
  const esperado = Buffer.from(`Bearer ${token}`)
  return recibido.length === esperado.length && timingSafeEqual(recibido, esperado)
}

async function json(req) {
  let texto = ''
  for await (const trozo of req) texto += trozo
  return JSON.parse(texto || '{}')
}

let siguiente = 1
http.createServer(async (req, res) => {
  if (!autorizado(req)) return res.writeHead(401).end()
  try {
    if (req.method === 'GET' && req.url === '/eventos') {
      res.writeHead(200, { 'Content-Type': 'application/x-ndjson' })
      res.write('{"tipo":"conectado"}\n')
      oyentes.add(res)
      req.on('close', () => oyentes.delete(res))
      return
    }
    if (req.method === 'POST' && req.url === '/tarea') {
      const { texto } = await json(req)
      if (typeof texto !== 'string' || !texto.trim()) return res.writeHead(400).end('falta texto')
      const id = String(siguiente++)
      await mcp.notification({ method: 'notifications/claude/channel', params: { content: texto, meta: { id } } })
      return res.writeHead(200, { 'Content-Type': 'application/json' }).end(JSON.stringify({ id }))
    }
    if (req.method === 'POST' && req.url === '/veredicto') {
      const { request_id, permitir } = await json(req)
      if (!/^[a-km-z]{5}$/.test(request_id ?? '')) return res.writeHead(400).end('request_id inválido')
      await mcp.notification({
        method: 'notifications/claude/channel/permission',
        params: { request_id, behavior: permitir === true ? 'allow' : 'deny' },
      })
      return res.writeHead(200, { 'Content-Type': 'application/json' }).end('{}')
    }
    res.writeHead(404).end()
  } catch (e) {
    res.writeHead(400).end(String(e))
  }
}).listen(PUERTO, '127.0.0.1')  // solo esta PC: el celular entra por vloomy.py, nunca directo acá
