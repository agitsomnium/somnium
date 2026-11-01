import { readFile, writeFile } from 'node:fs/promises';
import { createClient } from '@supabase/supabase-js';
const [configPath, resultPath, materialPath] = process.argv.slice(2);
const config = JSON.parse(await readFile(configPath, 'utf8'));
if (config.url !== 'https://jdfrottxrdhglxtqvtyx.supabase.co' || !config.publishableKey.startsWith('sb_publishable_')) throw new Error('Unexpected project or key type');
const client = createClient(config.url, config.publishableKey, { auth: { persistSession: false, autoRefreshToken: false, detectSessionInUrl: false } });
const checks = [];
for (const name of ['me', 'catalog', 'admin_members', 'admin_lessons', 'admin_directors', 'admin_audit', 'resource', 'redeem_code', 'issue_code', 'admin_series', 'materials', 'admin_materials']) {
  const { data, error } = await client.rpc(`somnium_${name}`, name === 'resource' ? { p_id: '00000000-0000-0000-0000-000000000000' } : name === 'materials' ? {p_lesson:'00000000-0000-0000-0000-000000000000'} : name === 'redeem_code' ? {p_code:'wrong'} : name === 'issue_code' ? {p_label:'wrong'} : {});
  checks.push({ name, denied: error?.code === '42501' && data === null, errorCode: error?.code ?? null });
}
const { data, error } = await client.schema('classroom_private').from('lessons').select('id');
checks.push({ name: 'private_schema_direct_access', denied: error?.code === 'PGRST106' && data === null, errorCode: error?.code ?? null });
if (materialPath) {
  if (!/^[a-f0-9-]{36}\.pdf$/.test(materialPath)) throw new Error('Unexpected material path');
  const {data, error} = await client.storage.from('somnium-materials').download(materialPath, {}, {cache:'no-store'});
  checks.push({name:'existing_private_pdf_anonymous_download',denied:!!error && data===null,errorCode:String(error?.statusCode ?? '')});
  const {data:publicLink} = client.storage.from('somnium-materials').getPublicUrl(materialPath);
  const publicResponse = await fetch(publicLink.publicUrl,{cache:'no-store'});
  checks.push({name:'existing_private_pdf_public_url',denied:!publicResponse.ok,errorCode:String(publicResponse.status)});
}
const receipt = { project: 'jdfrottxrdhglxtqvtyx', actualPostgrest: true, emailSent: false, checks, passed: checks.every(x => x.denied) };
await writeFile(resultPath, JSON.stringify(receipt, null, 2), { mode: 0o600 });
console.log(JSON.stringify(receipt));
if (!receipt.passed) process.exitCode = 1;
