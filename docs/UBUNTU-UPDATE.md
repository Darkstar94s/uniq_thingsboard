# تحديث UNIQ 4.3.1.4 على Ubuntu

## التوافق

هذه النسخة مبنية على الوسم الرسمي `v4.3.1.4`، commit `a488a4c138971c0264bf7fdc879871f68eead1e4`. كود الخادم وقاعدة البيانات وملفات التغليف والإعداد مطابقة لهذا الوسم. الاختلافات في الواجهة والتوثيق فقط. تستهدف Java 17 وتُبنى باستخدام JDK 21، بما يناسب سيرفر المستخدم: ThingsBoard `4.3.1.4-1` وJava 21.

لم يُنفذ أي تحديث على سيرفر الإنتاج. اختبر الحزمة على نسخة مستعادة من بياناتك قبل الإنتاج. لا تحتاج تعديلات الهوية نفسها تشغيل سكربت ترقية قاعدة البيانات.

## سحب المصدر

داخل نسخة المستودع، تأكد أن `git status --short` لا يظهر تعديلات محلية ثم:

```bash
git fetch origin
git switch bftech/uniq-4.3.1.4
git pull --ff-only origin bftech/uniq-4.3.1.4
```

فرع التوافق مستقل عن develop ومبني مباشرة على الإصدار الرسمي. لا يلزم force pull أو reset. سحب الكود لا يحدّث الحزمة المثبتة.

## بناء حزمة deb

على جهاز بناء Linux تتوفر فيه Maven وJDK 21 وأدوات البناء الأساسية:

```bash
java -version
mvn -version
mvn -B -ntp -pl application -am install \
  -DskipTests -Dlicense.skip=true \
  -Dpkg.skip.rpm=true -Dpkg.skip.zip=true
```

هذا يبني نسخة الإنتاج من Angular والخادم وحزمة `application/target/thingsboard.deb`. اختبارات Java تُتجاوز هنا؛ نجاح البناء وحده لا يثبت سلامة التشغيل على بياناتك. لا تستخدم `build.sh` لهذا الغرض لأنه يعطّل إنتاج الحزم. يحافظ اسم الحزمة والخدمة على `thingsboard` لتحديث التثبيت الحالي.

## قبل التثبيت

1. تحقق من `dpkg-query -W thingsboard` ومن أن الإصدار هو `4.3.1.4-1`.
2. انسخ قاعدة PostgreSQL الفعلية احتياطيًا واختبر الاستعادة في قاعدة منفصلة. احتفظ بنسخة خارج السيرفر.
3. احفظ محتويات `/usr/share/thingsboard/conf` الفعلية؛ `/etc/thingsboard/conf` قد يكون رابطًا إليها. احفظ أيضًا إعدادات systemd الإضافية والبيئة والشهادات والملفات المرفوعة وأي تخزين خارجي تستخدمه.
4. احتفظ بحزمة ThingsBoard السابقة. خصص فترة توقف قصيرة للتبديل.

مثال للنسخ فقط إذا كان اسم PostgreSQL المحلي `thingsboard`:

```bash
mkdir -p ~/uniq-backups
chmod 700 ~/uniq-backups
cd ~/uniq-backups
umask 077
backup_time=$(date +%Y%m%d-%H%M%S)
sudo -u postgres pg_dump -Fc thingsboard > "thingsboard-$backup_time.dump"
pg_restore --list "thingsboard-$backup_time.dump" > /dev/null
sudo tar -czf "config-$backup_time.tar.gz" -C /usr/share/thingsboard conf
```

توقف عند أي خطأ؛ نجاح `pg_restore --list` فحص أولي وليس بديلًا لاختبار الاستعادة. اسم القاعدة ليس مضمونًا؛ استخدم الاسم الموجود في إعداداتك دون مشاركة كلمات المرور.

## تحديث الحزمة المتوافقة

بعد نجاح النسخ الاحتياطي واختبار الحزمة، وفي مجلد حزمة UNIQ:

```bash
dpkg-deb -f ./thingsboard.deb Package Version
sudo systemctl stop thingsboard
sudo dpkg --force-confold -i ./thingsboard.deb
```

تحقق قبل التثبيت من أن اسم الحزمة `thingsboard` والإصدار `4.3.1.4-1`. `--force-confold` يحتفظ بالإعدادات المحلية المعدلة. إذا فشل dpkg، لا تتابع التشغيل قبل معالجة الخطأ أو الرجوع للحزمة السابقة. راجع ملفات الإعداد محليًا وتأكد من بقاء اتصال قاعدة البيانات نفسه. بعد نجاح التثبيت:

```bash
sudo systemctl daemon-reload
sudo systemctl start thingsboard
systemctl is-active thingsboard
sudo journalctl -u thingsboard -n 100 --no-pager
```

تحقق من الدخول بحسابك الحالي، والمستخدمين والأجهزة ولوحات المعلومات ووصول القياسات. حدّث ذاكرة المتصفح إن بقي الشعار القديم.

لا تشغّل `install.sh` أو `--loadDemo` أو `upgrade.sh` لهذا التحديث البصري على نفس الإصدار، ولا تحذف أو تعِد إنشاء قاعدة البيانات أو المستخدمين. لا تستخدم `apt purge`.

## الرجوع

إذا لم تتغير قاعدة البيانات، أوقف الخدمة وأعد تثبيت حزمة 4.3.1.4 السابقة مع الاحتفاظ بالإعدادات، ثم أعد التشغيل. لا تستعد نسخة قاعدة البيانات فوق قاعدة الإنتاج لمجرد الرجوع بالشعار؛ ذلك يفقد البيانات الأحدث. استعادة البيانات إجراء مستقل عند الحاجة الفعلية.
