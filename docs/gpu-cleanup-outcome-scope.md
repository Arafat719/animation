# Durable cleanup outcome scope review

2026-09-27। Review সম্পন্ন; implementation পরের micro-step।

## Evidence

- [Durable session](../animation_studio/providers/gpu_durable_session.py) closed/count
  persist করে কিন্তু cleanup result memory-only। Success-এর পর recovery আবার
  backend call/attempt খরচ করে; cap-এ আগের observation হারিয়ে unknown ফেরে।
- [Existing journal](../animation_studio/providers/gpu_journal.py) compute/storage/
  provider codes রাখে এবং absent/auth-failure/cap terminal করে। সেই semantics reuse;
  journal/watchdog পুনর্লিখন নয়।
- [CleanupResult](../animation_studio/providers/gpu_lifecycle.py)-এ complete মানে
  absent + storage none; saved observation-কে fresh/live result বলা যাবে না।

## পরের একটি micro-step

Session record-এ optional typed cleanup observation: resource identity, cleanup
attempt ordinal, compute/storage, allowlisted errors/provider codes। Raw error text
বা secrets নয়। Return API-তে saved/historical বনাম current-call source স্পষ্ট থাকবে।
Ordinal observation association-এর জন্য যথেষ্ট; নতুন timestamp dependency নয়।

1. Intent write → cleanup → observation atomic/fsync write। Result persistence
   failure propagate; admission closed এবং consumed attempt বজায় থাকবে।
2. পরের intent-এ পুরোনো observation clear করতে হবে; অথবা ordinal/current count
   mismatch হলে latest outcome unknown। Crash-এর পরে stale success reuse নয়।
3. Saved absent outcome-এ backend cleanup replay নয়। Storage none হলে historical
   complete; retained/unknown হলে historical needs-manual-cleanup। দুটোতেই live
   state unverified। Saved unauthorized-এ retry বন্ধ; live adapter যুক্ত নয়।
4. Nonterminal outcome-এ bounded explicit recovery; তিন-attempt cap reset নয়।
   Cap-এ saved observation report করা যাবে, কিন্তু current state unknown। Missing
   observation unknown; legacy record থেকে success অনুমান নয়।
5. Receipt/deadline/closed/owner-lock semantics অপরিবর্তিত। Historical complete
   billing-zero evidence নয়। Existing APIs-তে provenance চেনা যেতে হবে।

## Pass checks

- Successful close→reopen: saved outcome, zero backend calls, unchanged count।
- Unknown/retained storage false-complete নয়; auth-terminal retry নয়।
- Failure→bounded recovery, correct attempt association, cap-এ no increment।
- Crash/result-write/fsync failure: no false success/stale reuse, admission closed।
- Legacy absent field backward read; malformed resource/ordinal/state reject।
  Migration/backward-read policy নথিভুক্ত; relevant regression PASS।

একই Phase 4 local/mock authorization-এ পরের implementation করা যাবে। নতুন phase,
production DB/UI, paid GPU, network/install/model run নয়। Master requirements
অপরিবর্তিত। এই docs-only review-তে source/test consistency, links, plan drift,
whitespace ও RESUME length PASS; app tests নয়, prior 171-test evidence retained।
