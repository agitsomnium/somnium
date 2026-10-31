// One explicit, approved recipient only. No SMTP password or privileged key.
import { readFile, writeFile } from 'node:fs/promises';
import { createClient } from '@supabase/supabase-js';
const [configPath, receiptPath, approval] = process.argv.slice(2);
if (!configPath || !receiptPath || approval !== '--approved-somnium-one-email') {
  throw new Error('Requires protected client config, NEW receipt path and explicit one-email approval flag');
}
const config = JSON.parse(await readFile(configPath, 'utf8'));
if (config.url !== 'https://jdfrottxrdhglxtqvtyx.supabase.co' || !config.publishableKey?.startsWith('sb_publishable_')) {
  throw new Error('Only the Somnium staging project and a publishable key are allowed');
}
const receipt = { startedAt: new Date().toISOString(), project: 'jdfrottxrdhglxtqvtyx', purpose: 'one approved OTP email to Somnium Gmail', state: 'attempt_started', automaticRetry: false };
await writeFile(receiptPath, JSON.stringify(receipt, null, 2), { flag: 'wx', mode: 0o600 });
const supabase = createClient(config.url, config.publishableKey, { auth: { persistSession: false, autoRefreshToken: false, detectSessionInUrl: false } });
try {
  const { error } = await supabase.auth.signInWithOtp({ email: 'agit.somnium@gmail.com', options: { shouldCreateUser: true } });
  Object.assign(receipt, { finishedAt: new Date().toISOString(), state: error ? 'provider_rejected' : 'provider_accepted', code: error?.code ?? null, httpStatus: error?.status ?? null, deliveryConfirmed: false });
} catch {
  Object.assign(receipt, { finishedAt: new Date().toISOString(), state: 'outcome_unknown_do_not_resend', deliveryConfirmed: false });
}
await writeFile(receiptPath, JSON.stringify(receipt, null, 2), { mode: 0o600 });
console.log(JSON.stringify(receipt));
