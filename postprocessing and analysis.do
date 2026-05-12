local thresholds 23 25 27 29 31




foreach thre of local thresholds {
	import delimited "/Volumes/点我点我/all/Senior Spring/COS/rubric_scores_only_corrected.csv", varname(1) clear
    gen scam_`thre'_`thre' = (total_score >= `thre')


gen cplat_gen = "link_general" if category == "linkedin_general"
replace cplat_gen = "meta_general" if category == "meta_general"
gen cplat_tar = "link_targeted" if category == "linkedin_targeted"
replace cplat_tar = "meta_targeted" if category == "meta_targeted"
gen cterm_met = "meta_general" if category == "meta_general"
replace cterm_met = "meta_targeted" if category == "meta_targeted"
gen cterm_lin = "link_general" if category == "linkedin_general"
replace cterm_lin = "link_targeted" if category == "linkedin_targeted"
eststo clear

estpost ttest scam_`thre'_`thre', by(cplat_gen)
eststo cplat_gen

estpost ttest scam_`thre'_`thre', by(cplat_tar)
eststo cplat_tar

estpost ttest scam_`thre'_`thre', by(cterm_met)
eststo cterm_met

estpost ttest scam_`thre'_`thre', by(cterm_lin)
eststo cterm_lin


esttab cplat_gen cplat_tar cterm_met cterm_lin using "/Volumes/点我点我/all/Senior Spring/COS/results_`thre'.rtf", ///
    replace ///
    cells("mu_1 mu_2 b se p") ///
    label ///
	b(%9.3f) se(%9.3f) p(%9.3f) ///
    title("T-tests of scam_`thre' by treatment groups") ///
    compress


gen group = 1 if category == "linkedin_general"
replace group = 2 if category == "linkedin_targeted"
replace group = 3 if category == "meta_general"
replace group = 4 if category == "meta_targeted"

eststo clear

mean scam_`thre', over(group)
matrix list e(b)

nlcom (ratio_diff: (_b[c.scam_`thre'@3.group] /_b[c.scam_`thre'@4.group])- ( _b[c.scam_`thre'@1.group]/_b[c.scam_`thre'@2.group])), post

esttab using "/Volumes/点我点我/all/Senior Spring/COS/ratio_test_`thre'.rtf", replace ///
    b(%9.3f) se(%9.3f) ///
    star(* 0.10 ** 0.05 *** 0.01) ///
    label ///
    title("Test of ratio equality") ///
    compress

preserve
collapse (mean) mean_scam_`thre'=scam_`thre' (semean) se_scam_`thre'=scam_`thre', by(group)
gen ub = mean_scam_`thre' + 1.96*se_scam_`thre'
gen lb = mean_scam_`thre' - 1.96*se_scam_`thre'

label define group_lbl 1 "Linkedin General" 2 "Linkedin Targeted" 3 "Meta General" 4 "Meta Targeted"
label values group group_lbl

twoway ///
(rcap ub lb group) ///
(scatter mean_scam_`thre' group), ///
xlabel(1(1)4, valuelabel) ///
legend(off)

graph export "/Volumes/点我点我/all/Senior Spring/COS/graph_mean_ci_by_group_`thre'.png", replace width(2000)
restore


mean scam_`thre', over(group)
nlcom (ratio1:  _b[c.scam_`thre'@1.group]/_b[c.scam_`thre'@2.group]) (ratio2: _b[c.scam_`thre'@3.group]/_b[c.scam_`thre'@4.group]), post
test _b[ratio1] = _b[ratio2]

matrix b = e(b)
matrix V = e(V)

clear
set obs 2

gen ratio = .
gen se = .
gen name = ""

replace ratio = b[1,1] in 1
replace se    = sqrt(V[1,1]) in 1
replace name  = "LG/LT" in 1

replace ratio = b[1,2] in 2
replace se    = sqrt(V[2,2]) in 2
replace name  = "MG/MT" in 2

gen ub = ratio + 1.96*se
gen lb = ratio - 1.96*se

gen order = _n

twoway ///
(rcap ub lb order) ///
(scatter ratio order, msymbol(O)), ///
xlabel(1 "LG/LT" 2 "MG/MT") ///
ylabel(, angle(horizontal)) ///
xscale(range(0.5 2.3)) ///
xtitle("Ratios") ///
ytitle("Estimate") ///
legend(off)

graph export "/Volumes/点我点我/all/Senior Spring/COS/graph_ratio_mean_ci_`thre'.png", replace width(2000)
}


import delimited "/Volumes/点我点我/all/Senior Spring/COS/rubric_scores_only_corrected.csv", varname(1) clear
save "/Volumes/点我点我/all/Senior Spring/COS/rubric_scores_only_corrected.dta", replace


import delimited "/Volumes/点我点我/all/Senior Spring/COS/all_clean_ads_for_llm.csv", varname(1) clear bindquote(strict) maxquotedrows(1000)

merge 1:1 unique_id using "/Volumes/点我点我/all/Senior Spring/COS/rubric_scores_only_corrected.dta"

drop _merge
gen scam = (total_score>=27)
keep unique_id category ad_text total_score scam_`thre'
export excel "/Volumes/点我点我/all/Senior Spring/COS/for content analysis", replace firstrow(variables)







