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
    weighted_by_age=[]
    for age in rates.columns[1:]:
        eligible_age=counts[age].notna()
        base=int(counts.loc[eligible_age,0].sum())
        returning=int(counts.loc[eligible_age,age].sum())
        weighted_by_age.append({"age_months":int(age),"retention":returning/base,
          "eligible_cohorts":int(eligible_age.sum()),"eligible_base_customers":base})
    cells=[{"cohort":str(c),"age_months":int(a),"retention":float(rates.loc[c,a]),"customers":int(counts.loc[c,a])}
      for c in rates.index for a in rates.columns if pd.notna(rates.loc[c,a])]
    metrics={**audit,"complete_months":len(rates),"weighted_month_1_retention":weighted,
      "excluded_partial_month":str(partial),"weighted_retention_by_age":weighted_by_age,"cohort_cells":cells}
    fig,axes=plt.subplots(1,2,figsize=(14,5.7),gridspec_kw={"width_ratios":[2.2,1]})
    ax=axes[0]
    followup_max=float(np.nanmax(rates.iloc[:,1:].to_numpy())*100)
    im=ax.imshow(rates.values*100,cmap="Blues",vmin=0,vmax=followup_max,aspect="auto")
    ax.axvspan(-.5,.5,color="#e2e8f0",zorder=2)
    ax.set(xticks=range(len(rates.columns)),xticklabels=rates.columns,yticks=range(len(rates.index)),yticklabels=rates.index.astype(str),xlabel="Months after first observed purchase",ylabel="First observed cohort",title="Cohort repeat-purchase matrix")
    for row in range(len(rates)):
        for col in range(len(rates.columns)):
            val=rates.iloc[row,col]
            if pd.notna(val): ax.text(col,row,f"{val:.0%}",ha="center",va="center",fontsize=8,zorder=3,color="#15263e" if col==0 else ("white" if val*100>followup_max*.55 else "#15263e"))
    ax.text(0,-.72,"100% by definition",ha="center",va="bottom",fontsize=8,color="#475569")
    fig.colorbar(im,ax=ax,label="Follow-up customers returning (%)")
    aggregate=pd.DataFrame(weighted_by_age)
    axes[1].plot(aggregate.age_months,aggregate.retention*100,marker="o",color="#087f8c",linewidth=2)
    for row in aggregate.itertuples():
        axes[1].annotate(f"{row.retention:.0%}",xy=(row.age_months,row.retention*100),xytext=(0,6),textcoords="offset points",ha="center",fontsize=8)
    age_labels=[f"{row.age_months}\n{row.eligible_cohorts}" for row in aggregate.itertuples()]
    axes[1].set(title="Weighted return rate by month age",xlabel="Month age / eligible cohorts",ylabel="Returning customers (%)",xticks=aggregate.age_months,xticklabels=age_labels,ylim=(0,max(aggregate.retention*100)*1.25))
    axes[1].text(.02,.03,f"Eligible base changes by age\n{aggregate.eligible_cohorts.iloc[0]}→{aggregate.eligible_cohorts.iloc[-1]} cohorts · {aggregate.eligible_base_customers.iloc[0]:,}→{aggregate.eligible_base_customers.iloc[-1]:,} customers",transform=axes[1].transAxes,fontsize=8,color="#475569")
    finish(args.output_dir,"Cohort Retention",metrics,
      [f"Weighted month-1 repeat-purchase retention is {weighted:.1%} among cohorts with a full follow-up month.",
       "Compare cohorts at equal maturity; blank heatmap cells are not yet observable, not zero retention.",
       "Test an onboarding or follow-up intervention prospectively before claiming it improves retention."],
      ["First-observed cohorts are left-censored: pre-dataset purchase history is unknown.",
       "Final partial month excluded. Customers may return after skipping months; this is not survival retention.",
       "Only identified positive purchasers are included; no causal inference."],fig)
if __name__=="__main__": main()
