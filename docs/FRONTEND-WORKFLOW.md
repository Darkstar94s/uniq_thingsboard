# 🏠 UNIQ Smart Home — دليل تحديث الواجهة بدون بناء `.deb`

## 🎯 نظرة عامة: الحل الجديد السريع

بدلاً من بناء حزمة `.deb` ضخمة (تستغرق ساعات + موارد ضخمة)، سيُبنى الفرونت إند تلقائياً عبر **GitHub Actions** على خوادم GitHub المجانية، ويُنتج ملف ZIP خفيف (10-15 ميغابايت) جاهز للنشر في دقائق.

---

## 📋 طريقة العمل خطوة بخطوة

### الخطوة 1: تعديل الكود محلياً

```bash
# استنسخ المستودع (مرة واحدة فقط)
git clone https://github.com/YOUR_USERNAME/uniq_thingsboard.git
cd uniq_thingsboard

# أو إذا كان موجوداً، حدّثه
git pull origin main
```

### الخطوة 2: ارفع تعديلاتك لـ GitHub

```bash
# شاهد التغييرات
git status

# أضف الملفات المعدّلة
git add ui-ngx/src/

# اعمل commit
git commit -m "تحسين: [وصف التعديل]"

# ارفع للـ GitHub
git push origin main
```

### الخطوة 3: انتظر البناء التلقائي (5-15 دقيقة)

- افتح صفحة المستودع على GitHub
- اضغط على تبويب **Actions**
- ستجد Workflow باسم **"Build Frontend (ui-ngx)"** يعمل تلقائياً
- انتظر حتى يظهر ✅ أخضر

### الخطوة 4: حمّل ملف ZIP من GitHub

1. اضغط على الـ Workflow الناجح
2. انتقل لقسم **Artifacts** في أسفل الصفحة
3. اضغط لتحميل **`uniq-frontend-...`**

### الخطوة 5: نشر الواجهة على السيرفر (في أقل من دقيقة!)

```bash
# انسخ الملف للسيرفر
scp uniq-frontend-*.zip user@YOUR_SERVER_IP:/tmp/

# على السيرفر:
ssh user@YOUR_SERVER_IP

# فك الضغط ونشر الملفات
unzip /tmp/uniq-frontend-*.zip -d /tmp/tb-ui-new/

# نسخ الملفات لمجلد ThingsBoard
sudo cp -r /tmp/tb-ui-new/* /usr/share/thingsboard/bin/public/

# أو إذا كانت عبر Nginx:
sudo cp -r /tmp/tb-ui-new/* /var/www/thingsboard-ui/

# إعادة تشغيل ThingsBoard (اختياري إذا الملفات ساكنة فقط)
sudo systemctl restart thingsboard
```

---

## 🛠 بنية الملفات المُعدَّلة في هذا المشروع

```
ui-ngx/src/
├── assets/
│   ├── logo_title_dark.svg     ← شعار UNIQ للخلفيات الفاتحة (جديد)
│   ├── logo_title_white.svg    ← شعار UNIQ للخلفيات الداكنة
│   ├── logo_white.svg          ← شعار مصغر
│   └── uniq-favicon.svg        ← أيقونة المتصفح
├── app/
│   ├── modules/home/
│   │   ├── home.component.scss    ← تصميم الهيدر والسايدبار (فاتح+نظيف)
│   │   └── menu/
│   │       └── side-menu.component.scss  ← قائمة جانبية تفاعلية
│   ├── modules/login/pages/login/
│   │   ├── login.component.html   ← صفحة تسجيل الدخول
│   │   └── login.component.scss   ← تصميم بطاقة الدخول البيضاء
│   └── shared/components/
│       ├── logo.component.ts      ← منطق الشعار الذكي
│       └── logo.component.scss    ← تنسيق الشعار
└── scss/
    └── constants.scss             ← ألوان UNIQ الأساسية
```

---

## 🎨 هوية الألوان UNIQ

| الاسم | الكود | الاستخدام |
|-------|-------|---------|
| الأبيض | `#FFFFFF` | الخلفية الرئيسية، البطاقات |
| الأزرق الفاتح | `#7DA6FF` | الحدود، التأثيرات، الثانوي |
| الأزرق الداكن | `#0A57FC` | الأزرار، الأيقونات الفعالة، العناوين |
| خلفية فاتحة | `#F8FAFC` | خلفية الصفحة العامة |
| تمييز فاتح | `#EEF4FF` | خلفية العناصر النشطة |

---

## ❓ أسئلة شائعة

**س: كيف أعدّل نص معين في الواجهة؟**
- ابحث في `ui-ngx/src/` عن النص أو اسم الكومبوننت وعدّله

**س: لماذا لا أرى التغييرات على السيرفر؟**
- تأكد من مسح كاش المتصفح (Ctrl+Shift+R)
- تأكد من نسخ الملفات للمجلد الصحيح

**س: أين مجلد ThingsBoard على السيرفر؟**
```bash
# ابحث عنه
find /usr /opt /var -name "index.html" 2>/dev/null | grep -i thingsboard
```

**س: هل أحتاج لإعادة تشغيل ThingsBoard عند تغيير الواجهة فقط؟**
- إذا كانت الملفات الساكنة: **لا**، لا حاجة لإعادة التشغيل
- إذا كان ThingsBoard يخدم الملفات مباشرة: نعم، أعد التشغيل للتأكد
