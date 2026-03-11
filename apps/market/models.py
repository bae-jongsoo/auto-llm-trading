import hashlib

from django.db import models
from shared.models import CollectedRecord


class MarketSnapshot(CollectedRecord):
    per = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name="per",
    )
    pbr = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name="pbr",
    )
    eps = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name="eps",
    )
    bps = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name="bps",
    )
    stac_month = models.CharField(
        max_length=64,
        blank=True,
        default="",
        verbose_name="stac month",
    )
    lstn_stcn = models.CharField(
        max_length=128,
        blank=True,
        default="",
        verbose_name="lstn stcn",
    )
    hts_avls = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name="hts avls",
    )
    cpfn = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name="cpfn",
    )
    stck_fcam = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name="stck fcam",
    )
    w52_hgpr = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name="52week high price",
    )
    w52_hgpr_date = models.DateField(
        blank=True,
        null=True,
        verbose_name="52week high date",
    )
    w52_hgpr_vrss_prpr_ctrt = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name="52week high versus previous close rate",
    )
    w52_lwpr = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name="52week low price",
    )
    w52_lwpr_date = models.DateField(
        blank=True,
        null=True,
        verbose_name="52week low date",
    )
    w52_lwpr_vrss_prpr_ctrt = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name="52week low versus previous close rate",
    )
    d250_hgpr = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name="250day high price",
    )
    d250_hgpr_date = models.DateField(
        blank=True,
        null=True,
        verbose_name="250day high date",
    )
    d250_hgpr_vrss_prpr_rate = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name="250day high versus previous close rate",
    )
    d250_lwpr = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name="250day low price",
    )
    d250_lwpr_date = models.DateField(
        blank=True,
        null=True,
        verbose_name="250day low date",
    )
    d250_lwpr_vrss_prpr_rate = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name="250day low versus previous close rate",
    )
    stck_dryy_hgpr = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name="1year high price",
    )
    dryy_hgpr_date = models.DateField(
        blank=True,
        null=True,
        verbose_name="1year high date",
    )
    dryy_hgpr_vrss_prpr_rate = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name="1year high versus previous close rate",
    )
    stck_dryy_lwpr = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name="1year low price",
    )
    dryy_lwpr_date = models.DateField(
        blank=True,
        null=True,
        verbose_name="1year low date",
    )
    dryy_lwpr_vrss_prpr_rate = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name="1year low versus previous close rate",
    )
    hts_frgn_ehrt = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name="hts foreign investor ratio",
    )
    frgn_hldn_qty = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name="foreigner held quantity",
    )
    frgn_ntby_qty = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name="foreigner net buy quantity",
    )
    pgtr_ntby_qty = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name="program net buy quantity",
    )
    vol_tnrt = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name="volume turnover rate",
    )
    whol_loan_rmnd_rate = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name="whole loan remaining rate",
    )
    marg_rate = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name="margin rate",
    )
    crdt_able_yn = models.CharField(
        max_length=2,
        blank=True,
        default="",
        verbose_name="credit available",
    )
    ssts_yn = models.CharField(
        max_length=2,
        blank=True,
        default="",
        verbose_name="short sale",
    )
    iscd_stat_cls_code = models.CharField(
        max_length=16,
        blank=True,
        default="",
        verbose_name="market status code",
    )
    mrkt_warn_cls_code = models.CharField(
        max_length=16,
        blank=True,
        default="",
        verbose_name="market warning code",
    )
    invt_caful_yn = models.CharField(
        max_length=2,
        blank=True,
        default="",
        verbose_name="investment caution",
    )
    short_over_yn = models.CharField(
        max_length=2,
        blank=True,
        default="",
        verbose_name="short selling",
    )
    sltr_yn = models.CharField(
        max_length=2,
        blank=True,
        default="",
        verbose_name="surveillance target",
    )
    mang_issu_cls_code = models.CharField(
        max_length=16,
        blank=True,
        default="",
        verbose_name="management issue code",
    )
    temp_stop_yn = models.CharField(
        max_length=2,
        blank=True,
        default="",
        verbose_name="temporary stop",
    )
    oprc_rang_cont_yn = models.CharField(
        max_length=2,
        blank=True,
        default="",
        verbose_name="order price upper lower continuous",
    )
    clpr_rang_cont_yn = models.CharField(
        max_length=2,
        blank=True,
        default="",
        verbose_name="close price range continuous",
    )
    grmn_rate_cls_code = models.CharField(
        max_length=16,
        blank=True,
        default="",
        verbose_name="guarantee rate code",
    )
    new_hgpr_lwpr_cls_code = models.CharField(
        max_length=16,
        blank=True,
        default="",
        verbose_name="new high low range code",
    )
    rprs_mrkt_kor_name = models.CharField(
        max_length=128,
        blank=True,
        default="",
        verbose_name="representative market",
    )
    bstp_kor_isnm = models.CharField(
        max_length=128,
        blank=True,
        default="",
        verbose_name="market category name",
    )
    vi_cls_code = models.CharField(
        max_length=16,
        blank=True,
        default="",
        verbose_name="vi class code",
    )
    ovtm_vi_cls_code = models.CharField(
        max_length=16,
        blank=True,
        default="",
        verbose_name="overnight vi class code",
    )
    last_ssts_cntg_qty = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name="last short selling contract quantity",
    )
    apprch_rate = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name="approach rate",
    )

    @staticmethod
    def build_external_id(stock_code: str, published_at: str) -> str:
        return hashlib.sha256(f"{stock_code}|{published_at}".encode("utf-8")).hexdigest()

    def __str__(self) -> str:
        return f"{self.stock_code} @ {self.published_at or self.created_at}"
