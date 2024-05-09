import google.generativeai as genai
from db_connection import DatabaseConnection
from config import GEMINI_API_KEY

# Set up the model
generation_config = {
  "temperature": 0.1,
  "top_p": 0.95,
  "top_k": 0,
  "max_output_tokens": 10000,
}

database_connection = DatabaseConnection().connect()

def execute_django_query(query: str):
    print("From function calling")
    print(query)
    cur = database_connection.cursor()
    result = cur.execute(query=query)
    cur.close()
    return result
django_models = """
purchases/models.py
class Purchase(models.Model):

    ANDROID = "ANDROID"
    WEB = "WEB"
    GOOGLE_INAPP_BILLING = "GOOGLE_INAPP_BILLING"
    ACTIVE = "ACTIVE"
    INITIATED = "INITIATED"
    PENDING = "PENDING"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    CONSUMED = "CONSUMED"

    CLIENTS = (
        (ANDROID, "ANDROID"),
        (WEB, "WEB")
    )
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)
    expiry_date = models.DateTimeField(editable=True, null=True, blank=True)
    purchased_at = models.DateTimeField(editable=True, null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             related_name="purchases",
                             on_delete=models.CASCADE)

    # This exists because of historical reasons that nobody know of.
    product = models.ForeignKey(Product,
                                related_name="purchases",
                                null=True,
                                blank=True,
                                on_delete=models.SET_NULL)

    signup_key = models.CharField(max_length=20, default="NO-SIGNUP-KEY")
    mode_of_purchase = models.CharField(max_length=20,
                                        choices=MODES_OF_PURCHASE,
                                        default=MODES_OF_PURCHASE[0][0])
    purchase_type = models.CharField(max_length=20,
                                        choices=PURCHASE_TYPE,
                                        default=PURCHASE_TYPE[0][0])
    medium = models.CharField(max_length=20,
                              choices=PURCHASE_MEDIA,
                              default="ANDROID")
    purchase_status = models.CharField(max_length=20,
                                       choices=PURCHASE_STATUSES,
                                       default=PURCHASE_STATUSES[0][0])
    google_play_error_code = models.IntegerField(null=True, blank=True)
    google_play_purchase_token = models.CharField(max_length=400,
                                                  null=True,
                                                  blank=True)
    google_play_billing_status = models.CharField(max_length=20,
                                        choices=GOOGLE_PLAY_BILLING_STATUS,
                                        blank=True, null=True)
    # EMI Related fields
    is_initial_instalment = models.BooleanField(default=False)
    emi_status = models.CharField(max_length=20,
                                  choices=EMI_STATUSES,
                                  blank=True, null=True)
    parent_purchase = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        related_name="child_purchases",
        on_delete=models.SET_NULL)
    parent_emi_instalment = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        related_name="child_emis",
        on_delete=models.SET_NULL)
    total_amount_to_be_paid = models.IntegerField(default=0)
    emi_amount_to_pay = models.IntegerField(default=0)
    emi_expires_at = models.DateTimeField(editable=True, null=True, blank=True)
    total_instalments = models.IntegerField(default=1)
    instalment_no = models.IntegerField(default=1)
    remarks = models.TextField(default="")
    purchase_details_json = jsonfield(null=True, default=dict)
    # for app versions less than 583
    products = models.ManyToManyField(Product)
    plans = models.ManyToManyField(Plan,
                                   related_name="purchases")
    addon_plans = models.ManyToManyField(Plan,
                                         related_name="addon_purchases")
    coupon = models.ForeignKey("coupons.Coupon", related_name='purchase_logs',
                               null=True, blank=True, on_delete=models.CASCADE)
    # nullable for backward compatibility
    expires_at = models.DateTimeField(null=True, blank=True)
    total_amount = models.IntegerField(default=0)
    discount = models.IntegerField(default=0)
    coupon_code_worth = models.IntegerField(default=0)
    wallet_balance_used = models.IntegerField(default=0)
    amount_to_pay = models.IntegerField(default=0)
    captured_amount = models.IntegerField(default=0)
    entris_revenue_share = models.IntegerField(default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        related_name="created_purchases", on_delete=models.CASCADE)
    # Unique Hash ID to identify each product.
    hash_id = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    client = models.CharField(
        choices=settings.CLIENTS,
        max_length=20,
        default=settings.ANDROID
    )
    objects = managers.PurchaseManager()
    completed_onboarding = models.BooleanField(
        default=False,
        null=True,
        blank=True)
    # Field to store details of buyer who initiates a gift purchase via landingpage.
    buyer_details = jsonfield(null=True, default=dict)
    upgraded_from_purchase = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
    invoice = models.FileField(
        null=True,
        blank=True,
        upload_to="invoice/%Y/%m/%d"
    )

    #selling price of plan while purchase
    plan_selling_price =models.IntegerField(
        default=0,
        verbose_name="Current selling price of plan")
    # These fields were added for Lead squared integration purpose it is the unique key stored in leadsquared side
    prospect_event_id = models.CharField(max_length=255,blank=True, null=True)
    activity_code = models.IntegerField(blank=True, null=True)

    landing_page_details = jsonfield(default=dict, null=True)
    receipt = models.FileField(
        null=True,
        blank=True,
        upload_to="receipt/%Y/%m/%d"
    )
    # Used for attributing purchase to campaign
    attribution_data = jsonfield(null=True, default=dict)

    def __str__(self):
        return "{}-{}".format(self.mode_of_purchase, self.user.username)

    #Added as part of Advanced payment will be removed once all fields are migrated
    def save(self, *args, **kwargs):
        if not self.pk:
            if self.purchase_type=='EMI' and self.parent_purchase and \
                self.parent_purchase.purchase_type == 'EMI':
                self.parent_emi_instalment = self.parent_purchase
            elif self.purchase_type=='EMI' and self.is_initial_instalment:
                self.emi_amount_to_pay = self.total_amount_to_be_paid
            elif self.parent_purchase and self.parent_purchase.purchase_status == 'UPGRADED':
                self.upgraded_from_purchase = self.parent_purchase
        super(Purchase, self).save(*args, **kwargs)

    @property
    def is_child_emi(self):
        if self.purchase_type == 'EMI' and not \
            self.is_initial_instalment:
            return True
        return False

purchases/models.py
class Plan(TimestampedModel):
    # for readability in backend, not shown anywhere inapp
    name = models.CharField(max_length=100)
    # Holding this field only for data migration purposes
    # this will be same as the product code.
    is_active = models.BooleanField(default=False)
    code = models.CharField(max_length=50)
    product_package = models.ForeignKey(
        ProductPackage, on_delete=models.CASCADE,
        related_name="plans")
    # plan validity in days
    validity = models.IntegerField(default=365,
                                   verbose_name="Plan validity in days")
    # MRP of the plan
    actual_price = models.IntegerField(
        default=0,
        verbose_name="Actual price of the plan")
    # Discounted price
    selling_price = models.IntegerField(
        default=0,
        verbose_name="Current selling price")
    lowest_selling_price = models.IntegerField(
        default=0,
        verbose_name="Min selling price")
    google_play_product_id = models.CharField(null=True,
                                              blank=True,
                                              max_length=50)
    # If the plan is under A/B testing, Map the particular
    # experiment here.
    experiment = models.ForeignKey(Experiment, null=True,
                                   blank=True,
                                   related_name="plans",
                                   on_delete=models.SET_NULL)
    # bucket to which offer coupon belong.
    # should be less than or equal to the number
    # of buckets
    bucket = models.IntegerField(
        default=0,
        verbose_name="Users in which bucket should see this plan?",
        help_text="It should be less than or equal to the to"
        "the total number of buckets defined in experiment")
    has_addon_plans = models.BooleanField(default=False)
    addon_plans = models.ManyToManyField(
        "self",
        blank=True,
        help_text="Extra plans that user gets while buying a particular plan")
    sms_text = models.CharField(null=True,
                                blank=True,
                                max_length=200)
    enable_in_product = models.BooleanField(default=True)
    properties = jsonfield(default=dict, blank=True)

    def __str__(self):
        return "{}-{}".format(self.name, self.validity)

purchases/models.py
class ProductPackage(TimestampedModel):
    PRODUCT_PACKAGE_CATEGORIES = (
        ("TRACK", "Track based"),
        ("PACK", "Pack based"),
        ("COMBO", "Pack and track combo"),
        ("UNLIMITED", "Entri Unlimited(All tracks)"),
        ("PLATFORM", "Platform based")
    )
    CATEGORY_TYPES = (
        ("REGULAR", "Regular product"),
        ("GOLD", "Gold product"),
        ("ELEVATE", "Elevate product"),
        ("SUPER_GOLD", "Super Gold product"),
    )
    COURSE_VERTICAL = (
        ("SKILLING", "Skilling courses"),
        ("TESTPREP", "Test preparation courses")
    )
    description = models.TextField(blank=False, null=True)
    description_localized = jsonfield(
        null=True,
        default=default_name_localized
    )
    detailed_description = models.TextField(blank=False, null=True)
    detailed_description_localized = jsonfield(
        null=True, default=default_name_localized)
    name = models.CharField(max_length=100)
    name_localized = jsonfield(
        null=True,
        default=default_name_localized
    )
    intro_video = jsonfield(null=True, default=default_name_localized, help_text='Add youtube video ids (for Gold Landing page).\
                                                                    Eg: {"en": "p4yVRSKmF0o","ml":"p4yVRSKmF0o"}')
    video_urls = jsonfield(
        null=True,
        default=dict,
        help_text='Add youtube videos. Eg: {"tutorial_videos": {"en": "https://www.youtube.com/watch?v=oiJPKNp7r3I"},\
              "intro_videos": {"en": "https://www.youtube.com/watch?v=oiJPKNp7r3I"},}'
    )
    buttons = jsonfield(default=dict, null=True, blank=True)
    category = models.CharField(max_length=10,
                                choices=PRODUCT_PACKAGE_CATEGORIES,
                                default="TRACK")
    category_type = models.CharField(max_length=10,
                                choices=CATEGORY_TYPES,
                                default="REGULAR")
    course_vertical = models.CharField(max_length=10,
                                choices=COURSE_VERTICAL,
                                blank=True, null=True)
    tracks = models.ManyToManyField(PlatformGroup,
                                    related_name='product_packages',
                                    blank=True,
                                    verbose_name='Validity Applicable Tracks',
                                    help_text='Select the tracks applicable for this product package.\
                                     Product validity is provided for tracks selected here.')
    include_subscribed_tracks = models.ManyToManyField(PlatformGroup,
                                                       related_name='included_product_packages',
                                                       blank=True,
                                                       verbose_name='Tracks to be Subscribed',
                                                       help_text='Select the tracks to be subscribed by the user to show this product package.\
                                     Users subscribed to any of the track specified here will see this product package.')
    exclude_subscribed_tracks = models.ManyToManyField(PlatformGroup,
                                                       related_name='excluded_product_packages',
                                                       blank=True,
                                                       verbose_name='Exclude Tracks',
                                                       help_text='Select the tracks to be excluded for this product package.\
                                     Users subscribed to the tracks specified here will not see this product package.')
    # For gold,there can be multiple gold products for a track
    default_product_track = models.ForeignKey(
                                PlatformGroup,
                                null=True,
                                blank=True,
                                related_name="default_product_packages", on_delete=models.SET_NULL)
    premium_features = models.ManyToManyField(
        PremiumFeatures, related_name="product_packages", blank=True)
    packs = models.ManyToManyField(Pack,
                                   related_name='product_packages', blank=True,)
    platforms = models.ManyToManyField(Platform,
                                   related_name='product_packages', blank=True,)
    user_feedbacks = jsonfield(blank=True, null=False, default=list, help_text='Add testimonials (for Gold Landing page).\
                                                                    <br>Eg: [{"name": "Vipinsaj", "dp_url": "https://cloudfront-videos.entri.app/media/tamil_teachers/satheesh.png", "feedback": " I was preparing for PSC for last 3 years, I always score 2,3 marks less than cut off, as I was never able to score more than 30% in Maths and English, through Entri Gold special classes and tasks now I\'m able to score 8+ in both English and Maths.", "user_details": " Kerala PSC aspirant"}, {"name": "Arun", "dp_url": "https://cloudfront-videos.entri.app/media/hindi_teachers/mirza_ehtisham_beg.png", "feedback": "As a beginner I had no idea where to start and how to complete this vast syllabus, my mentor conducted exams and identified my weak and strong areas and prepared a study plan for me which helped me to complete syllabus.", "user_details": " Kerala PSC aspirant"}]')
    # Shall remove this field once datas are migrated to "teachers" field
    teachers_json = jsonfield(blank=True, null=False, default=list, help_text='Add teacher biographies (for Gold Landing page).\
                                                                    <br>Eg: [{"name": "Sabeeh", "dp_url": "https://cloudfront-videos.entri.app/media/hindi_teachers/mirza_ehtisham_beg.png", "biography": "15+ years of PSC teaching career"}, {"name": "Neethu", "dp_url": "https://cloudfront-videos.entri.app/media/hindi_teachers/mirza_ehtisham_beg.png", "biography": "15+ years of PSC teaching career"}]')
    teachers = models.ManyToManyField("user_accounts.Teacher",
                                  related_name="product_packages", blank=True)
    ordering_weight = models.IntegerField(default=1)
    icon_url = models.CharField(max_length=200, null=True, blank=False)
    banner_image = models.CharField(max_length=200, null=True, blank=True)
    is_active = models.BooleanField(default=False)
    languages = models.ManyToManyField(
        "scaffold.Language", related_name="product_packages")
    entris_revenue_percentage = models.IntegerField(default=100)
    enable_in_web = models.BooleanField(default=False)
    enable_in_android = models.BooleanField(default=True)
    onboarding_questions_weights = jsonfield(
        null=True, blank=True, default=list)
    resources_available = jsonfield(default=dict, blank=True)
    enable_enquire = models.BooleanField(default=False)
    enquire_url = models.CharField(max_length=200, null=True, blank=True)
    copy_mapped_object_data = models.BooleanField(default=False)
    slack_channel_data = jsonfield(
        default=dict, null=True, blank=True)
    revenue_attributions = jsonfield(
        default=dict,
        help_text='''
        {
            "business_course_revenue_attributions": [
                {
                    "course_id": 123,
                    "course_category": "TRACK/PACK/PLATFORM",
                    "course_type": "REGULAR/GOLD/ELEVATE/SUPER_GOLD",
                    "share_percentage": 50
                }
            ]
        }
        '''
    )

    def __str__(self):
        return "{}-{}".format(self.name, self.category)
"""

system_instruction = (
    "Your helpful assistance generate a Django orm query for the prompt from the model"
    "Only generate and execute the query"
    "Dont explain the code"
    f'use this models {django_models}')
def generate_response(chat_instance, promtp):
    response = chat_instance.send_message(promtp, stream=False)
    return response.text

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(model_name="gemini-1.5-pro-latest",
    generation_config = generation_config,
                              system_instruction=system_instruction,
                               tools=[execute_django_query],)
chat_instance = model.start_chat(enable_automatic_function_calling=True)
response = chat_instance.send_message("Calculate total revenue of top 5 plans", stream=False)
print(response.text)
database_connection.close()
