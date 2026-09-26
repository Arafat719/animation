# কাজ শুরু করার ছোট পথ

- বাংলায় সংক্ষিপ্ত numbered উত্তর দাও। মালিকের বর্তমান নির্দেশ scope নির্ধারণ করে।
- প্রথমে শুধু `docs/RESUME.md` পড়ো। সাধারণ প্রশ্নে প্রয়োজন ছাড়া plan/source পড়বে না।
- Implementation হলে `docs/plan/rules.md`, RESUME-তে দেওয়া বর্তমান phase এবং
  সংশ্লিষ্ট source/test পড়ো। সব phase, master plan বা পুরোনো report একসঙ্গে পড়বে না।
- একবারে একটি অনুমোদিত অসম্পূর্ণ micro-step; completed কাজ restart নয়।
  নতুন phase-এর অনুমোদন দরকার; আগের authorization থাকলে আবার চাইবে না।
- `docs/plan/INDEX.md` প্রয়োজনভিত্তিক reference map। Feature requirements-এর মূল
  উৎস master plan; excerpts তার হুবহু নির্বাচিত অংশ। সন্দেহ হলে শুধু সংশ্লিষ্ট
  heading খুঁজে পড়ো। পূর্ণ master শুধু পূর্ণ plan audit/revision প্রয়োজন হলে পড়ো।
- কাজ শেষে RESUME-তে outcome, checks, blocker ও next step সংক্ষেপে লেখো;
  বিস্তারিত completion history `docs/current-build-status.md`-এ রাখো।
- Requirements বদলালে master edit করে `python3 scripts/build_plan_docs.py` চালাও;
  `python3 scripts/build_plan_docs.py --check` দিয়ে excerpt drift যাচাই করো।
- Paid GPU/billable resource বা >2 GB model download-এর আগে explicit approval।
  Secrets/personal assets commit নয়; unrelated edits সংরক্ষণ করো।

