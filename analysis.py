from utils import arguments, retail, theme, finish, plt, pd, np
def main():
    args=arguments(); theme()
    _,p,audit=retail(args.data_dir,identified=True)
    # Drop the partial final month before both acquisition and activity calculations.
    partial=p.InvoiceDate.max().to_period("M")
    p=p[p.InvoiceDate.dt.to_period("M")<partial].copy()
    p["month"]=p.InvoiceDate.dt.to_period("M")
    p["cohort"]=p.groupby("CustomerID").month.transform("min")
    p["age"]=p.month.astype("int64")-p.cohort.astype("int64")
    counts=p.groupby(["cohort","age"]).CustomerID.nunique().unstack()
    last=p.month.max()
    for cohort in counts.index:
        for age in counts.columns:
            if age<=last.ordinal-cohort.ordinal and pd.isna(counts.loc[cohort,age]):
                counts.loc[cohort,age]=0
    rates=counts.div(counts[0],axis=0)
    assert np.allclose(rates[0],1)
    observed=rates.stack().dropna()
    assert ((observed>=0)&(observed<=1)).all()
    eligible=counts[1].notna()
    weighted=counts.loc[eligible,1].sum()/counts.loc[eligible,0].sum()
    cells=[{"cohort":str(c),"age_months":int(a),"retention":float(rates.loc[c,a]),"customers":int(counts.loc[c,a])}
      for c in rates.index for a in rates.columns if pd.notna(rates.loc[c,a])]
    metrics={**audit,"complete_months":len(rates),"weighted_month_1_retention":weighted,
      "excluded_partial_month":str(partial),"cohort_cells":cells}
    fig,ax=plt.subplots(figsize=(11,6))
    im=ax.imshow(rates.values*100,cmap="Blues",vmin=0,vmax=100,aspect="auto")
    ax.set(xticks=range(len(rates.columns)),xticklabels=rates.columns,yticks=range(len(rates.index)),yticklabels=rates.index.astype(str),xlabel="Months after first observed purchase",ylabel="First observed cohort",title="Repeat-purchase retention · complete months only")
    for row in range(len(rates)):
        for col in range(len(rates.columns)):
            val=rates.iloc[row,col]
            if pd.notna(val): ax.text(col,row,f"{val:.0%}",ha="center",va="center",fontsize=8,color="white" if val>.5 else "#15263e")
    fig.colorbar(im,ax=ax,label="Customers returning (%)")
    finish(args.output_dir,"Cohort Retention",metrics,
      [f"Weighted month-1 repeat-purchase retention is {weighted:.1%} among cohorts with a full follow-up month.",
       "Compare cohorts at equal maturity; blank heatmap cells are not yet observable, not zero retention.",
       "Test an onboarding or follow-up intervention prospectively before claiming it improves retention."],
      ["First-observed cohorts are left-censored: pre-dataset purchase history is unknown.",
       "Final partial month excluded. Customers may return after skipping months; this is not survival retention.",
       "Only identified positive purchasers are included; no causal inference."],fig)
if __name__=="__main__": main()
